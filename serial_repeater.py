import socket
from serial import Serial
from threading import Thread
from queue import Queue


active_queues = []

def broadcast_event(data):
    for q in active_queues:
        q.put(data)

class Outlet(Thread):
    def __init__(self, name='Unnamed Outlet'):
        super().__init__()
        self.name = name
        self.mailbox = Queue()
        #active_queues.append(self.mailbox)

    def run(self):
        while True:
            data = self.mailbox.get()
            if data == 'shutdown':
                print('shutting down outlet: ', self.name)
                return
            print('received a message:', data)

    def send(self, data):
        raise NotImplementedError("send method not implemented")

    def stop(self):
        #active_queues.remove(self.mailbox)
        self.mailbox.put("shutdown")
        self.join()

class SerialOutlet(Outlet):
    def __init__(self, port, baudrate=9600):
        super().__init__(f"SerialOutlet({port})")
        self.serial = Serial(port, baudrate)

    def send(self, data):
        self.serial.write(data)

    def stop(self):
        super().stop()
        print(f"Closing serial port: {self.serial.port}")
        self.serial.close()
        print(f"Serial port {self.serial.port} closed successfully.")

class TCPClientOutlet(Outlet):
    def __init__(self, host, port):
        super().__init__(f"TCPClientOutlet({host}:{port})")
        self.host = host
        self.port = port
        # Initialize TCP connection here
        self.sock = socket.create_connection((host, port), timeout=1)
        self.send_and_receive_command("HELLO;", "OK;")

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


class SerialRepeater(Thread):
    def __init__(self, port, baudrate=9600, timeout=1):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.stop_event = False
        self.outlets = []

    def add_outlet(self, outlet):
        self.outlets.append(outlet)

    def run(self):
        self.serial = Serial(self.port, self.baudrate, timeout=self.timeout)
        buffer = bytearray()

        # start all outlets
        for outlet in self.outlets:
            outlet.start()

        while not self.stop_event:
            try:
                data = self.serial.read_until(b';')
                if not data:
                    continue

                buffer.extend(data)
                while b';' in buffer:
                    terminator_index = buffer.index(b';')
                    message = bytes(buffer[:terminator_index + 1])
                    print(f"Received: {message!r}")
                    if message == b'disconnect;':
                        print("Received disconnect command. Stopping repeater.")
                        self.stop()
                        return
                    for outlet in self.outlets:
                        outlet.send(message)
                    del buffer[:terminator_index + 1]
            except Exception as e:
                print(f"Error occurred: {e}, {e.__class__.__name__}")
                break

    def stop(self):
        if self.serial is not None:
            print(f"Closing serial port: {self.serial.port}")
            self.serial.close()
            print(f"Serial port {self.serial.port} closed successfully.")
        for outlet in self.outlets:
            outlet.stop()
        self.stop_event = True

if __name__ == "__main__":
    repeater = SerialRepeater(port='COM7', baudrate=9600)
    outlet1 = TCPClientOutlet(host='128.120.140.228', port=8282)
    outlet2 = SerialOutlet(port='COM8', baudrate=9600)
    repeater.add_outlet(outlet1)
    repeater.add_outlet(outlet2)
    repeater.start()    # this starts the repeater thread, which will start each of the outlet threads
    repeater.join()

    # try:
    # except KeyboardInterrupt:
    #     print("Shutting down...")
    #     repeater.stop()
    #     outlet1.stop()
    #     #   outlet2.stop()

    # print("All threads stopped. outlet1.join().")
    # outlet1.join()
    # # outlet2.join()
    # print("outlet1.join() complete. releasing repeater_thread.")
    # repeater.join()
    # print("repeater_thread.join() complete. Exiting.")