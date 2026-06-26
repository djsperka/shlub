import socket
from time import sleep as sleep
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)

if __name__ == "__main__":
    parser = ArgumentParser(description='Serial port repeater.', formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--port', required=True, help='tcp port to listen on')
    args = parser.parse_args()
    print(f"port {args.port}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, int(args.port)))
        s.listen()
        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            data = conn.recv(1024)
            if data:
                print(f'Received {data.decode().strip()}')
                conn.sendall(b'OK;')

                while True:
                    cmd = conn.recv(1024)
                    if not cmd:
                        break
                    else:
                        print(f"received: {cmd.decode().strip()}")
