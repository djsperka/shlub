from outlet import Outlet, SerialOutlet, TCPClientOutlet
from threading import Event, Thread
from time import sleep as sleep
import socket
from serial import Serial

import sys
if sys.platform=="linux":
    # This is good/bad on linux, not in lab.
    GOOD_SERIAL_PORT="/home/dan/mydev/ttyV0"
    BAD_SERIAL_PORT="COM6"
    TCP_HOST = "127.0.0.1"
    TCP_PORT = 9990
elif sys.platform=="win32":
    GOOD_SERIAL_PORT="COM6"
    BAD_SERIAL_PORT="COM99"
    TCP_HOST = "127.0.0.1"
    TCP_PORT = 9990



def test_good_serial():
    connect_event = Event()
    disconnect_event = Event()
    outlet = SerialOutlet(GOOD_SERIAL_PORT, connect_event=connect_event, disconnect_event=disconnect_event)
    outlet.start()
    assert(outlet.is_alive())

    connect_event.set()
    sleep(1)
    assert(outlet.is_alive())

    disconnect_event.set()
    sleep(1)
    assert(not outlet.is_alive())
    outlet.join()


def test_bad_serial():
    connect_event = Event()
    disconnect_event = Event()
    outlet = SerialOutlet(BAD_SERIAL_PORT, connect_event=connect_event, disconnect_event=disconnect_event)
    outlet.start()
    assert(outlet.is_alive())

    connect_event.set()
    sleep(1)
    assert(not outlet.is_alive())

    disconnect_event.set()
    sleep(1)
    assert(not outlet.is_alive())
    outlet.join()

def test_good_tcp():
    host = SimpleHost(TCP_HOST, TCP_PORT)
    host.start()
    assert(host.is_alive())

    connect_event = Event()
    disconnect_event = Event()
    outlet = TCPClientOutlet(TCP_HOST, TCP_PORT, connect_event=connect_event, disconnect_event=disconnect_event)
    outlet.start()
    assert(outlet.is_alive())

    connect_event.set()
    sleep(1)
    assert(outlet.is_alive())

    disconnect_event.set()
    sleep(1)
    assert(not outlet.is_alive())

    outlet.join()
    host.join()


def test_tcp_no_host():
    connect_event = Event()
    disconnect_event = Event()
    outlet = TCPClientOutlet(TCP_HOST, TCP_PORT, connect_event=connect_event, disconnect_event=disconnect_event)
    outlet.start()
    assert(outlet.is_alive())

    connect_event.set()
    sleep(3)
    assert(not outlet.is_alive())

    disconnect_event.set()
    sleep(1)
    assert(not outlet.is_alive())

    outlet.join()





class SimpleHost(Thread):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((TCP_HOST, TCP_PORT))
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
