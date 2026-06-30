import socket
from serial import Serial
from threading import Thread, Event
from queue import Queue
from time import sleep as sleep


class Outlet(Thread):
    def __init__(self, name:str, **kwargs):
        """Base class for repeater outlets (places where repeater input is sent)

        Args:
            connect_event (Event): Event that is set when this outlet should connect to its destination.
            name (str, optional): _description_. Defaults to 'Unnamed Outlet'.
        """
        super().__init__()
        self.connect_event:Event = kwargs.pop('connect_event')
        self.stop_event:Event = kwargs.pop('stop_event')
        self.name = name
        self.mailbox = Queue()
        self.connected = False

    def run(self):

        # Wait until connect event is set
        print(f"Outlet {self.name} waiting to connect...")
        while not self.connect_event.is_set():
            sleep(0.1)

        # Now try to connect
        if not self.connect():
            self.connected = False
            print(f"Outlet {self.name} could not be connected.")
            return
        else:
            print(f"Outlet {self.name} connected.")
            self.connected = True

        # Now loop until stop is requested
        while not self.stop_event.is_set(): 
            if not self.mailbox.empty():
                data = self.mailbox.get()
                self.send(data)
            else:
                sleep(0.1)
        self.disconnect()
        print(f"Outlet {self.name} ending thread.")

    def connect(self) -> bool:
        """Connect this outlet to its destination
        Subclasses should NOT raise errors! Return False instead

        Returns:
            bool: True if connection is successful        
        """
        return False

    def disconnect(self):
        """Disconnect this outlet from its destination

        Raises:
            NotImplementedError: Subclasses must implement
        """
        raise NotImplementedError("send method not implemented")


    def send(self, data):
        """Send the string to the destination of this outlet.

        Args:
            data (str): message to send (should include terminator)

        Raises:
            NotImplementedError: subclasses must implement
        """
        raise NotImplementedError("send method not implemented")

class SerialOutlet(Outlet):
    def __init__(self, port:str, baudrate:int=9600, **kwargs):
        super().__init__(f"SerialOutlet({port})", **kwargs)
        self.serial = Serial()
        self.serial.port = port
        self.serial.baudrate = baudrate

    def connect(self) -> bool:
        """Open serial port

        Returns:
            bool: True if connection successful
        """
        try:
            self.serial.open()
        except Exception as e:
            print(f"Serial outlet cannot open: {e}, {e.__class__.__name__}")
            return False
        print(f"Outlet {self.name} opened.")
        return True
    
    def disconnect(self):
        if self.serial.is_open:
            print(f"Closing serial port: {self.serial.port}")
            self.serial.close()
            print(f"Serial port {self.serial.port} closed.")
        self.connected = False

    def send(self, data):
        print(f"serialsending {data}")
        self.serial.write(data)

    def stop(self):
        self.serial.close()
    
class TCPClientOutlet(Outlet):
    def __init__(self, host: str, port: int, **kwargs):
        super().__init__(f"TCPClientOutlet({host}:{port})", **kwargs)
        self.host = host
        self.port = port

    def connect(self) ->bool:
        # Initialize TCP connection here
        b = False
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=1)
            b= self.send_and_receive_command("HELLO;", "OK;")
        except Exception as e:
            print(f"TCPClient cannot connect: {e}")
        return b

    def send(self, data):
        # Send data over TCP connection here
        print(f"tcp send {data}")
        self.sock.sendall(data)

    def disconnect(self):
        # Close TCP connection here
        print(f"Closing tcp port: {self.host}:{self.port}")
        self.sock.close()
        print(f"Closing tcp port: {self.host}:{self.port} - done")
        self.connected = False
        

    def send_and_receive_command(self, command: str, expected_response: str) -> bool:
        self.send(command.encode())
        response = self.sock.recv(1024).decode().strip()
        print(f"Sent: {command!r} -> Received: {response!r}")
        if response != expected_response:
            print(f"Unexpected response: {response!r}, expected: {expected_response!r}")
            return False
        return True
