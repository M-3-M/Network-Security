# flag: netsec{0n3_l1n3_4t_4_t1m3_bd8c98b2}

import socket
import threading

HOST = "0.0.0.0"
PORT = 9001

store = {}


def handle_command(line):
    parts = line.strip().split(" ", 2)
    cmd = parts[0].upper() if parts else ""

    if cmd == "PING":
        return "PONG"

    if cmd == "ECHO":
        return line.strip()[len("ECHO ") :]

    if cmd == "SET" and len(parts) >= 3:
        store[parts[1]] = parts[2]
        return "OK"

    if cmd == "GET" and len(parts) >= 2:
        return store.get(parts[1], "NOT_FOUND")

    return "ERR"


def handle_client(conn, addr):
    with conn:
        print(f"Connected by {addr}")
        buffer = ""
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break

                buffer += data.decode("utf-8")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip("\r")
                    print("Command:", line)

                    try:
                        response = handle_command(line)
                    except ConnectionError as e:
                        print(e)
                        response = "ERR"

                    print("Response:", response)
                    conn.sendall((response + "\n").encode("utf-8"))
        except ConnectionError as e:
            print(f"Client {addr} error: {e}")
        print(f"Disconnected {addr}")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Listening on {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            threading.Thread(
                target=handle_client, args=(conn, addr), daemon=True
            ).start()


if __name__ == "__main__":
    main()
