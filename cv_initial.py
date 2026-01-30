import os
import time
import cv2
import numpy as np

# Try to support both Colab and local environments for displaying images
try:
    from google.colab.patches import cv2_imshow  # type: ignore
    _IN_COLAB = True
except Exception:
    cv2_imshow = None
    _IN_COLAB = False


def find_camera(preferred_name_substr="camo", max_index=4, backends=None, timeout=1.0):
    """
    Try to find a working camera device. Prefer backends in order.
    If CAMO_DEVICE_INDEX env var is set, try that index first.
    Returns (cap, index, backend) or (None, None, None).
    """
    if backends is None:
        # Prefer Media Foundation on Windows (virtual cameras often register there),
        # then DirectShow, then default.
        backends = [getattr(cv2, "CAP_MSMF", None), getattr(cv2, "CAP_DSHOW", None), None]

    # If the user supplied an index via env var, try it first
    env_idx = os.getenv("CAMO_DEVICE_INDEX")
    if env_idx is not None:
        try:
            idx = int(env_idx)
            for backend in backends:
                if backend is None:
                    cap = cv2.VideoCapture(idx)
                else:
                    cap = cv2.VideoCapture(idx, backend)
                t0 = time.time()
                while time.time() - t0 < timeout:
                    ret, _ = cap.read()
                    if ret:
                        return cap, idx, backend
                cap.release()
        except Exception:
            pass

    # Probe indices and backends
    for backend in backends:
        for idx in range(0, max_index + 1):
            try:
                if backend is None:
                    cap = cv2.VideoCapture(idx)
                else:
                    cap = cv2.VideoCapture(idx, backend)
                t0 = time.time()
                while time.time() - t0 < timeout:
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        # simple heuristic: return first working device
                        return cap, idx, backend
                cap.release()
            except Exception:
                try:
                    cap.release()
                except Exception:
                    pass
    return None, None, None


def main():
    # --- CONFIGURATION ---
    ID_TL = 0
    ID_TR = 1
    ID_BR = 2
    ID_BL = 3
    TARGET_IDS = {ID_TL, ID_TR, ID_BR, ID_BL}

    # NEW: explicit 500x500 target for the requested transform/assignment
    ASSIGN_SIZE = (500, 500)  # width, height in pixels

    # NEW: which marker ids to compute pose for (ids 7,8,9)
    POSE_IDS = {7, 8, 9}

    # --- CAMERA SETUP ---
    cap, used_index, used_backend = find_camera(preferred_name_substr="camo", max_index=6)

    if cap is None or not cap.isOpened():
        print("Error: Unable to open camera. If you know the device index for Camo, set CAMO_DEVICE_INDEX environment variable (e.g. set CAMO_DEVICE_INDEX=1).")
        return

    backend_name = "CAP_MSMF" if used_backend == getattr(cv2, "CAP_MSMF", None) else ("CAP_DSHOW" if used_backend == getattr(cv2, "CAP_DSHOW", None) else "default")
    print(f"Opened camera index {used_index} using backend {backend_name}.")

    # Use a reasonable resolution for the virtual camera (Camo may not support ultra-high sizes)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    # --- ArUco setup with API compatibility ---
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

    if hasattr(cv2.aruco, "DetectorParameters_create"):
        parameters = cv2.aruco.DetectorParameters_create()
    else:
        parameters = cv2.aruco.DetectorParameters()

    detector = None
    if hasattr(cv2.aruco, "ArucoDetector"):
        try:
            detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
        except Exception:
            detector = None

    print("Camera started. Align markers 0, 1, 2, 3 in frame.")
    if _IN_COLAB:
        print("Running in Colab mode: will process one frame and exit.")
    else:
        print("Press 'q' in the display window to quit.")

    # variable to hold the latest 500x500 assigned image
    assigned_500 = None

    # persistent storage for poses of ids 7,8,9 (rows: id, cx, cy, angle_deg)
    poses_array = np.empty((0, 4), dtype=float)

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("Warning: empty frame received.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect markers (support detector object or legacy function)
        if detector is not None:
            corners, ids, rejected = detector.detectMarkers(gray)
        else:
            corners, ids, rejected = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

        if ids is not None:
            detected_ids_set = set(ids.flatten())

            if TARGET_IDS.issubset(detected_ids_set):
                marker_centers = {}

                # NEW: accumulate poses for POSE_IDS this frame
                poses_list = []

                for i, marker_id in enumerate(ids.flatten()):
                    # accumulate centers for corner markers (0,1,2,3)
                    if marker_id in TARGET_IDS:
                        c = corners[i][0]
                        cx = int(c[:, 0].mean())
                        cy = int(c[:, 1].mean())
                        marker_centers[marker_id] = [cx, cy]

                    # compute center + direction for ids 7,8,9
                    if marker_id in POSE_IDS:
                        c = corners[i][0]  # shape (4,2) ordered [tl, tr, br, bl]
                        cx = float(c[:, 0].mean())
                        cy = float(c[:, 1].mean())
                        # direction: angle of top edge (from top-left to top-right)
                        dx = float(c[1, 0] - c[0, 0])
                        dy = float(c[1, 1] - c[0, 1])
                        angle_rad = np.arctan2(dy, dx)
                        angle_deg = float(np.degrees(angle_rad))
                        poses_list.append([float(marker_id), cx, cy, angle_deg])

                # store poses for external use (array shape Nx4)
                if len(poses_list) > 0:
                    poses_array = np.array(poses_list, dtype=float)
                else:
                    poses_array = np.empty((0, 4), dtype=float)

                # CONTINUOUS PRINT: print poses_array every frame when non-empty
                if poses_array.size > 0:
                    # print header then each pose on its own line
                    print("Poses (id, cx, cy, angle_deg):")
                    for row in poses_array:
                        print(f"{int(row[0])}, {row[1]:.2f}, {row[2]:.2f}, {row[3]:.2f}")
                # Ensure we have all required centers before proceeding with the 500x500 warp
                if len(marker_centers) == 4:
                    src_pts = np.array([
                        marker_centers[ID_TL],
                        marker_centers[ID_TR],
                        marker_centers[ID_BR],
                        marker_centers[ID_BL]
                    ], dtype="float32")

                    # ONLY create the 500x500 perspective transform and assign it
                    w500, h500 = ASSIGN_SIZE
                    dst_pts_500 = np.array([
                        [0, 0],
                        [w500 - 1, 0],
                        [w500 - 1, h500 - 1],
                        [0, h500 - 1]
                    ], dtype="float32")

                    M500 = cv2.getPerspectiveTransform(src_pts, dst_pts_500)
                    warped_500 = cv2.warpPerspective(frame, M500, (w500, h500))

                    # assign to the persistent variable so other code can use it
                    assigned_500 = warped_500

                    # display the 500x500 image in its own window
                    if _IN_COLAB and cv2_imshow is not None:
                        cv2_imshow(assigned_500)
                    else:
                        cv2.imshow("Warped 500x500", assigned_500)

            # draw markers for feedback
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

        # display main feed (resized)
        display_frame = cv2.resize(frame, (800, 600))
        if _IN_COLAB and cv2_imshow is not None:
            cv2_imshow(display_frame)
            # In Colab we show one frame and exit (no interactive windows)
            break
        else:
            cv2.imshow("Camera Feed", display_frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            # optional: press 's' to save the latest assigned 500x500 image
            if key == ord('s') and assigned_500 is not None:
                cv2.imwrite("assigned_500.png", assigned_500)
                print("Saved assigned_500.png")
            # optional: press 'p' to print poses_array to console
            if key == ord('p'):
                print("Poses (id, cx, cy, angle_deg):")
                print(poses_array)

    cap.release()
    if not _IN_COLAB:
        cv2.destroyAllWindows()
    print(poses_array)


if __name__ == "__main__":
    main()
