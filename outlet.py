import socket
from serial import Serial
from threading import Thread, Event
from queue import Queue
from time import sleep as sleep
import logging

logger = logging.getLogger(__name__)

class Outlet(Thread):
    def __init__(self, name:str, **kwargs):
        """Base class for repeater outlets (places where repeater input is sent)
        An outlet will run in its own thread. On startup it will try to connect. When
        the connection is established, the outlet will then wait on its own queue, repeating anything
        it receives through its output connection. If the initial connection fails, the thread ends. The thread is 
        stopped by setting the disconnect_event. The property 'connected' is set to False when thread ends. 

        Args:
            connect_event (Event): Event that is set when this outlet should connect to its destination.
            name (str, optional): _description_. Defaults to 'Unnamed Outlet'.
        """
        super().__init__()
        self.disconnect_event:Event = kwargs.pop('disconnect_event')
        self.name = name
        self.mailbox = Queue()
        self.connected = False

    def run(self):

        logger.info(f"Starting outlet: {self.name} {self.connected}")
        self.connect()
        if self.connected:
            logger.info(f"Outlet {self.name} connected. {self.connected}")
        else:
            logger.warning(f"Outlet {self.name} could not be connected.")
            return

        # Now loop until disconnect is requested
        while not self.disconnect_event.is_set(): 
            if not self.mailbox.empty():
                data = self.mailbox.get()
                self.send(data)
            else:
                sleep(0.1)
        self.disconnect()
        logger.info(f"Outlet {self.name} ending thread.")

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
        self.serial.timeout = 0

    def connect(self) -> bool:
        """Open serial port

        Returns:
            bool: True if connection successful
        """
        try:
            logger.info(str(type(self.serial)))
            self.serial.open()
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

        except Exception as e:
            logger.error(f"SerialOutlet error: {e}")
            return False
        logger.info(f"Outlet {self.name} opened.")
        self.connected = True
        return True
    
    def disconnect(self):
        if self.serial.is_open:
            logger.info(f"Closing serial port: {self.serial.port}")
            self.serial.close()
            logger.info(f"Serial port {self.serial.port} closed.")
            self.connected = False

    def send(self, data):
        logger.info(f"{self.name} sending {data}")
        self.serial.write(data)
        logger.info(f"{self.name} sending {data} - done")

    def stop(self):
        self.serial.close()
    
class TCPClientOutlet(Outlet):
    def __init__(self, host: str, port: int, **kwargs):
        super().__init__(f"TCPClientOutlet({host}:{port})", **kwargs)
        self.host = host
        self.port = port
        self.sock = None

    def connect(self) ->bool:
        # Initialize TCP connection here
        if self.connected:
            return True
        else:
            try:
                self.sock = socket.create_connection((self.host, self.port), timeout=1)
                if not self.send_and_receive_command("HELLO;", "OK;"):
                    self.disconnect()
                else:
                    self.connected = True
            except Exception as e:
                logger.error(f"TCPClient cannot connect: {e}")
        return self.connected

    def send(self, data):
        # Send data over TCP connection here
        logger.info(f"{self.name} sending {data}")
        self.sock.sendall(data)
        logger.info(f"{self.name} sending {data} - done")

    def disconnect(self):
        # Close TCP connection here
        logger.info(f"Closing tcp port: {self.host}:{self.port}")
        self.sock.close()
        logger.info(f"Closing tcp port: {self.host}:{self.port} - done")
        self.connected = False
        

    def send_and_receive_command(self, command: str, expected_response: str) -> bool:
        self.send(command.encode())
        response = self.sock.recv(1024).decode().strip()
        logger.info(f"Sent: {command!r} -> Received: {response!r}")
        if response != expected_response:
            logger.error(f"Unexpected response: {response!r}, expected: {expected_response!r}")
            return False
        return True
