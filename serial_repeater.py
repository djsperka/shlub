import socket
from serial import Serial
from threading import Thread
from queue import Queue


active_queues = []

def broadcast_event(data):
    for q in active_queues:
        q.put(data)

class Outlet(Thread):
    def __init__(self):
        super().__init__()
        self.mailbox = Queue()
        active_queues.append(self.mailbox)

    def run(self):
        while True:
            data = self.mailbox.get()
            if data == 'shutdown':
                print('shutting down')
                return
            print('received a message:', data)

    def send(self, data):
        raise NotImplementedError("send method not implemented")

    def stop(self):
        active_queues.remove(self.mailbox)
        self.mailbox.put("shutdown")
        self.join()

class SerialOutlet(Outlet):
    def __init__(self, port, baudrate=9600):
        super().__init__()
        self.serial = Serial(port, baudrate)

    def send(self, data):
        self.serial.write(data)

    def stop(self):
        super().stop()
        self.serial.close()

class TCPClientOutlet(Outlet):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        # Initialize TCP connection here
        self.sock = socket.create_connection((host, port), timeout=1)
        self.send_and_receive_command("HELLO", "OK;")

    def send(self, data):
        # Send data over TCP connection here
        self.sock.sendall(data)

    def stop(self):
        super().stop()
        # Close TCP connection here
        self.sock.close()

    def send_and_receive_command(self, command: str, expected_response: str) -> str:
        self.send(command.encode())
        response = self.sock.recv(1024).decode().strip()
        print(f"Sent: {command!r} -> Received: {response!r}")
        if response != expected_response:
            raise ValueError(f"Unexpected response: {response!r}, expected: {expected_response!r}")
        return response


class SerialRepeater:
    def __init__(self, port, baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

    def run(self):
        self.serial = Serial(self.port, self.baudrate, timeout=self.timeout)
        buffer = bytearray()

        while True:
            try:
                data = self.serial.read_until(b';')
                if not data:
                    continue

                buffer.extend(data)
                while b';' in buffer:
                    terminator_index = buffer.index(b';')
                    message = bytes(buffer[:terminator_index + 1])
                    print(f"Received: {message!r}")
                    broadcast_event(message)
                    del buffer[:terminator_index + 1]
            except Exception as e:
                print(f"Error occurred: {e}")
                break

    def stop(self):
        if self.serial is not None:
            self.serial.close()