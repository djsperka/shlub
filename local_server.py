import socket
from time import sleep as sleep
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from threading import Thread
import logging


logger = logging.getLogger(__name__)
HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 9999

class SingleClientServer(Thread):
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.stopped = False
        super().__init__()

    def stop(self):
        self.stopped = True

    def run(self):
        logger.info(f"Open socket on {self.host}:{self.port}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            s.bind((self.host, int(self.port)))
            s.listen()

            while not self.stopped:
                try: 
                    (conn, addr) = s.accept() 
                except socket.timeout:
                    pass
                else:
                    with conn:
                        logger.info(f"Connected by {addr}")
                        data = conn.recv(1024)
                        if data:
                            logger.info(f'Received {data.decode().strip()}')
                            conn.sendall(b'OK;')

                            while True:
                                cmd = conn.recv(1024)
                                if not cmd:
                                    break
                                else:
                                    logger.info(f"received: {cmd.decode().strip()}")



if __name__ == "__main__":
    parser = ArgumentParser(description='Serial port repeater.', formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--port', required=True, help='tcp port to listen on')
    args = parser.parse_args()
    svr = SingleClientServer(host=HOST, port=args.port)

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
