import socket
from serial import Serial
from threading import Thread, Event
from queue import Queue
from time import sleep
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

class Outlet(Thread):
    def __init__(self, connect_event:Event , name:str='Unnamed Outlet'):
        """Base class for repeater outlets (places where repeater input is sent)

        Args:
            connect_event (Event): Event that is set when this outlet should connect to its destination.
            name (str, optional): _description_. Defaults to 'Unnamed Outlet'.
        """
        super().__init__()
        self.event = connect_event
        self.name = name
        self.mailbox = Queue()
        self.connected = False
        self.stop_requested = False

    def run(self):

        # Wait until connect event is set
        print(f"Outlet {self.name} waiting to connect...")
        while not self.event.is_set():
            sleep(0.1)

        # Now try to connect
        if not self.connect():
            raise RuntimeError("Cannot connect")
        else:
            print(f"Outlet {self.name} connected.")
            self.connected = True

        # Now loop until stop is requested
        while not self.stop_requested:            
            data = self.mailbox.get()
            self.send(data)
        self.disconnect()

    def connect(self) -> bool:
        """Connect this outlet to its destination

        Raises:
            NotImplementedError: Subclasses must implement this

        Returns:
            bool: True if connection is successful        
        """

        raise NotImplementedError("send method not implemented")
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
    def __init__(self, event:Event, port:str, baudrate:int=9600):
        super().__init__(event, f"SerialOutlet({port})")
        self.serial = Serial()
        self.serial.port = port
        self.serial.baudrate = baudrate

    def connect(self):
        """Open serial port

        Returns:
            bool: True if connection successful
        """
        try:
            self.serial.open()
        except Exception as e:
            print(f"Error occurred: {e}, {e.__class__.__name__}")
        print(f"Outlet {self.name} opened.")
        return self.serial.is_open
    
    def disconnect(self):
        if self.serial.is_open:
            self.serial.close()
        return

    def send(self, data):
        print(f"sending {data}")
        self.serial.write(data)

    def stop(self):
        print(f"Closing serial port: {self.serial.port}")
        self.serial.close()
        print(f"Serial port {self.serial.port} closed successfully.")

class TCPClientOutlet(Outlet):
    def __init__(self, event: Event, host: str, port: int):
        super().__init__(event, f"TCPClientOutlet({host}:{port})")
        self.host = host
        self.port = port

    def connect(self) ->bool:
        # Initialize TCP connection here
        self.sock = socket.create_connection((self.host, self.port), timeout=1)
        return self.send_and_receive_command("HELLO;", "OK;")

    def send(self, data):
        # Send data over TCP connection here
        self.sock.sendall(data)

    def stop(self):
        # Close TCP connection here
        self.sock.close()

    def send_and_receive_command(self, command: str, expected_response: str) -> bool:
        self.send(command.encode())
        response = self.sock.recv(1024).decode().strip()
        print(f"Sent: {command!r} -> Received: {response!r}")
        if response != expected_response:
            print(f"Unexpected response: {response!r}, expected: {expected_response!r}")
            return False
        return True


class SerialRepeater(Thread):
    def __init__(self, port, baudrate=9600, timeout=1):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.start_event = Event()
        self.stop_requested = False
        self.outlets = []

    def add_outlet(self, outletstring: str):
        """Add an outlet to the repeater using the config string.

        Config string should be in the form <serial,port> for a serial outlet, e.g. "serial,COM7". 
        Config string should be in the form <tcp,host,port> for a tcp outlet.


        Args:
            outletstring (str): config string from command line
        """
        print(f"Adding outlet with config: {astring}")
        l = astring.split(",")
        if len(l) > 0:
            if l[0].lower() == "serial" and len(l)==2:
                self.outlets.append(SerialOutlet(self.start_event, l[1]))
            elif l[0].lower() == "tcp" and len(l)==3:
                self.outlets.append(TCPClientOutlet(self.start_event, l[1], int(l[2])))
            else:
                raise ValueError(f"Cannot open outlet with argument {astring}")

    def run(self):
        self.serial = Serial(self.port, self.baudrate, timeout=self.timeout)
        buffer = bytearray()

        # start all outlets
        for outlet in self.outlets:
            outlet.start()
        self.start_event.set()

        while not self.stop_requested:
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
    parser = ArgumentParser(description='Serial port repeater.', formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--port', required=True, help='serial port to listen on')
    parser.add_argument('--baudrate', default=9600, type=int, help='baud rate for incoming port. Default=9600')
    parser.add_argument('--outlet', action='append', required=True, help='Specify serial/tcp e.g. serial,COM7 or tcp,host,port')
    args = parser.parse_args()

    print(f"port {args.port}")
    print(f"outlets: {len(args.outlet)}")

    try:
        repeater = SerialRepeater(port=args.port, baudrate=args.baudrate)
        for astring in args.outlet:
            repeater.add_outlet(astring)
        repeater.start()    # this starts the repeater thread, which will start each of the outlet threads
        repeater.join()
    except Exception as e:
        print(f"Error occurred: {e}, {e.__class__.__name__}")

    # # try:
    # # except KeyboardInterrupt:
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