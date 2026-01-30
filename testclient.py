import socket
import time

SERVER_IP = "127.0.0.1"   # change if server is remote
SERVER_PORT = 5555

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    client_socket.connect((SERVER_IP, SERVER_PORT))
    print("✅ Connected to server")

    while True:
        message = input("Send message (type 'exit' to quit): ")

        if message.lower() == "exit":
            break

        client_socket.sendall(message.encode("utf-8"))

        time.sleep(0.1)

except Exception as e:
    print(f"❌ Connection error: {e}")

finally:
    client_socket.close()
    print("🔌 Client disconnected")
