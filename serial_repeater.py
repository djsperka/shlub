import socket
from serial import Serial
from threading import Thread, Event
from queue import Queue
from time import sleep as sleep
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

class Outlet(Thread):
    def __init__(self, name:str, **kwargs):
        """Base class for repeater outlets (places where repeater input is sent)

        Args:
            connect_event (Event): Event that is set when this outlet should connect to its destination.
            name (str, optional): _description_. Defaults to 'Unnamed Outlet'.
        """
        super().__init__()
        self.connect_event = kwargs.pop('connect_event')
        self.stop_event = kwargs.pop('stop_event')
        self.name = name
        self.mailbox = Queue()
        self.connected = False

    def run(self):

        # Wait until connect event is set
        print(f"Outlet {self.name} waiting to connect...")
        while not self.connect_event.is_set():
            sleep(0.1)

        # Now try to connect
        try:
            self.connect()
            print(f"Outlet {self.name} connected.")
            self.connected = True
        except Exception as e:
            print(f"Outlet connection for {self.name} failed: {e}.")
            return

        # Now loop until stop is requested
        while not self.stop_event.is_set(): 
            if not self.mailbox.empty():
                data = self.mailbox.get()
                self.send(data)
            else:
                sleep(0.1)
        print(f"Thread {self.name} DISCONNNECTing")
        self.disconnect()
        print(f"Thread {self.name} ending")

    def connect(self) -> None:
        """Connect this outlet to its destination

        Raises:
            NotImplementedError: Subclasses must implement this

        """

        raise NotImplementedError("send method not implemented")

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

    def connect(self):
        """Open serial port

        """
        print(f"connect serial open? {self.serial.is_open}")
        self.serial.close()
        self.serial.open()
        print(f"Outlet {self.name} opened.")
   
    def disconnect(self):
        if self.serial.is_open:
            print(f"Closing serial port: {self.serial.port}")
            self.serial.close()
            print(f"Serial port {self.serial.port} closed.")

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

    def connect(self):
        # Initialize TCP connection here
        self.sock = socket.create_connection((self.host, self.port), timeout=1)
        if not self.send_and_receive_command("HELLO;", "OK;"):
            raise RuntimeError('HELLO/OK handshake failed.')

    def send(self, data):
        # Send data over TCP connection here
        print(f"tcp send {data}")
        self.sock.sendall(data)

    def disconnect(self):
        # Close TCP connection here
        print(f"Closing tcp port: {self.host}:{self.port}")
        self.sock.close()
        print(f"Closing tcp port: {self.host}:{self.port} - done")
        
    def send_and_receive_command(self, command: str, expected_response: str) -> bool:
        self.send(command.encode())
        response = self.sock.recv(1024).decode().strip()
        print(f"Handshake for {self.name}: {command!r} -> Received: {response!r}")
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
        self.connect_event = Event()
        self.stop_event = Event()
        self.outlets = []
        self.running = False

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
                self.outlets.append(SerialOutlet(l[1], connect_event=self.connect_event, stop_event=self.stop_event))
            elif l[0].lower() == "tcp" and len(l)==3:
                self.outlets.append(TCPClientOutlet(l[1], int(l[2]), connect_event=self.connect_event, stop_event=self.stop_event))
            else:
                raise ValueError(f"Cannot open outlet with argument {astring}")

    def connect_all(self) -> bool:
        # set connection event
        self.connect_event.set()

        # now wait a couple of seconds for outlets to connect
        waitcount = 0
        waitready = False
        while waitcount<10 and not waitready:
            waitready = True
            for outlet in self.outlets:
                if not outlet.connected:
                    waitready = False
            sleep(0.1)
            waitcount += 1
        return waitready

    def run(self):
        self.serial = Serial(self.port, self.baudrate, timeout=self.timeout)
        buffer = bytearray()

        # start all outlets
        for outlet in self.outlets:
            outlet.start()

        # connect outlets to their destinations
        if self.connect_all():
            self.running = True    
            while not self.stop_event.is_set():
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
                        else:
                            for outlet in self.outlets:
                                outlet.send(message)
                        del buffer[:terminator_index + 1]
                except Exception as e:
                    print(f"Error occurred: {e}, {e.__class__.__name__}")
                    break
        else:
            # stop any outlet threads that were opened
            self.stop_event.set()

        for outlet in self.outlets:
            outlet.join()


    def stop(self):
        if self.serial is not None:
            print(f"Closing serial port: {self.serial.port}")
            self.serial.close()
            print(f"Serial port {self.serial.port} closed successfully.")
        self.stop_event.set()
        self.running = False


if __name__ == "__main__":
    parser = ArgumentParser(description='Serial port repeater.', formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--port', required=True, help='serial port to listen on')
    parser.add_argument('--baudrate', default=9600, type=int, help='baud rate for incoming port. Default=9600')
    parser.add_argument('--outlet', action='append', required=True, help='Specify serial/tcp e.g. serial,COM7 or tcp,host,port')
    args = parser.parse_args()

    print(f"port {args.port}")
    print(f"outlets: {len(args.outlet)}")
    repeater = SerialRepeater(port=args.port, baudrate=args.baudrate)

    try:
        for astring in args.outlet:
            repeater.add_outlet(astring)
        repeater.start()    # this starts the repeater thread, which will start each of the outlet threads
    except Exception as e:
        print(f"Error occurred: {e}, {e.__class__.__name__}")
        exit()

    sleep(2)
    
    print("starting loop")
    try:
        while repeater.running:
            sleep(.1)
    except KeyboardInterrupt:
        print("caught keyboard interrupt.")
        repeater.stop()

    print("loop done - join repeater")
    repeater.join()



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

    # python serial_repeater.py --port COM7 --outlet serial,COM8 --outlet tcp,128.120.140.228,8282