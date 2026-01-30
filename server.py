import socket
import threading


class ThreadedSocketServer:
    def __init__(self, host="127.0.0.1", port=5555, max_clients=10):
        self.host = host
        self.port = port
        self.max_clients = max_clients

        self.server_socket = None
        self.is_running = False

        # NEW: store connected clients
        self.clients = []              # list of (conn, addr)
        self.clients_lock = threading.Lock()  # thread safety

    def start_server(self):
        """Start the socket server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(self.max_clients)

            self.is_running = True
            print(f"✅ Server started on {self.host}:{self.port}")

            threading.Thread(
                target=self._accept_clients,
                daemon=True
            ).start()

        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            self.is_running = False

    def _accept_clients(self):
        """Accept incoming client connections"""
        print("🔄 Waiting for clients...")

        while self.is_running:
            try:
                conn, addr = self.server_socket.accept()
                print(f"🟢 Client connected: {addr}")

                # ADD client to list
                with self.clients_lock:
                    self.clients.append((conn, addr))

                threading.Thread(
                    target=self._handle_client,
                    args=(conn, addr),
                    daemon=True
                ).start()

            except Exception as e:
                if self.is_running:
                    print(f"⚠️ Accept error: {e}")

    def _handle_client(self, conn, addr):
        """Handle a connected client"""
        try:
            while True:
                data = conn.recv(1024)

                if not data:
                    break

                message = data.decode("utf-8")
                print(f"📩 From {addr}: {message}")

        except Exception as e:
            print(f"⚠️ Client error {addr}: {e}")

        finally:
            print(f"🔴 Client disconnected: {addr}")

            # REMOVE client from list
            with self.clients_lock:
                self.clients = [
                    (c, a) for (c, a) in self.clients if c != conn
                ]

            conn.close()

    def stop_server(self):
        """Stop the socket server"""
        self.is_running = False

        # Close all client connections
        with self.clients_lock:
            for conn, _ in self.clients:
                conn.close()
            self.clients.clear()

        if self.server_socket:
            self.server_socket.close()

        print("🛑 Server stopped")

    def server_status(self):
        """Return True if server is running, else False"""
        return self.is_running

    def client_count(self):
        """Return number of connected clients"""
        with self.clients_lock:
            return len(self.clients)
