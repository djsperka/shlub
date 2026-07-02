from serial import Serial
from threading import Thread, Event
from time import sleep as sleep
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from outlet import Outlet, SerialOutlet, TCPClientOutlet
from typing import List
from enum import Enum
import traceback


A_WINK = 0.1    # Time to sleep

class SerialRepeater(Thread):

    def __init__(self, port, baudrate=9600, outlets:List[str] = [], timeout=1, autoconnect = False):
        super().__init__()
        self.port:str = port
        self.baudrate:int = baudrate
        self.timeout:float = timeout
        self.serial:None|Serial = None
        self.connect_event:Event|None = None
        self.stop_event:Event|None = None
        self.outlets:List[str] = outlets
        self.autoconnect = autoconnect
        self._o:List[Outlet] = []
        self.is_connected: bool = False
        self.connect_requested = False
        self.running = False

    def add_outlet(self, outletstring: str):
        """Add an outlet to the repeater using the config string.

        Config string should be in the form <serial,port> for a serial outlet, e.g. "serial,COM7". 
        Config string should be in the form <tcp,host,port> for a tcp outlet.


        Args:
            outletstring (str): config string from command line
        """
        self.outlets.append(outletstring)


    def connect_all(self) -> bool:
        """Create and connect all outlets

        Raises:
            ValueError: If an outlet string is misconfigured, this is raised.

        Returns:
            bool: True if all outlets created and connected successfully.
        """

        print("connect_all()")
        if self.is_connected:
            print("connect_all: already connected.")
            return True

        # new events
        self.connect_event = Event()
        self.stop_event = Event()

        bFail = False
        for outletstring in self.outlets:
            print(f"Adding outlet with config: {outletstring}")
            l = outletstring.split(",")
            if len(l) > 0:
                if l[0].lower() == "serial" and len(l)==2:
                    o = SerialOutlet(l[1], connect_event=self.connect_event, stop_event=self.stop_event)
                    o.start()
                    self._o.append(o)
                elif l[0].lower() == "tcp" and len(l)==3:
                    o = TCPClientOutlet(l[1], int(l[2]), connect_event=self.connect_event, stop_event=self.stop_event)
                    o.start()
                    self._o.append(o)
                else:
                    print(f"Cannot open outlet with argument {outletstring}")
                    bFail = True

        # Check that all threads started. if not, stop then and bail.
        if len(self._o)<len(self.outlets):
            self.stop_event.set()
            for o in self._o:
                o.join()
            return False

        # set connection event - this starts outlet threads
        self.connect_event.set()

        # now wait a couple of seconds for outlets to connect (only tcp outlet might take time)
        waitcount = 0
        waitready = True
        while waitcount<10 and not waitready:
            for outlet in self._o:
                if not outlet.connected:
                    print(f"({waitcount}) {outlet.name} not connected...")
                    waitready = False
                    break
            sleep(0.1)
            waitcount += 1
        if waitready:
            print("exited loop, True")
            self.is_connected = True
        else:
            print("exited loop, False")
            self.connect_event = None
            self.stop_event = None
        return waitready

    def run(self):
        print("starting repeater...")
        self.serial = Serial(self.port, self.baudrate, timeout=self.timeout)
        buffer = bytearray()
        self.running = True

        if self.autoconnect:
            print("autoconnecting...")
            self.connect_all()
            self.autoconnect = False    # only try this once

        while self.running:

            if self.stop_event and self.stop_event.is_set():
                break

            try:
                if not self.serial.is_open:
                    print("WARN ser closed")
                data = self.serial.read_until(b';')
                if not data:
                    continue

                buffer.extend(data)
                while b';' in buffer:
                    terminator_index = buffer.index(b';')
                    message = bytes(buffer[:terminator_index + 1])
                    print(f"Received: {message!r}")

                    # specioal case: connect
                    if message == b'connect;':
                        if not self.is_connected:
                            self.is_connected = self.connect_all()
                            for outlet in self._o:
                                print(f"outlet {outlet.name} conn? {str(outlet.connected)}")
                            break
                        else:
                            print('already connected')
                    elif message == b'disconnect;':
                        print("Received disconnect command. Stopping repeater.")
                        self.stop()
                    else:
                        for outlet in self._o:
                            outlet.send(message)
                    del buffer[:terminator_index + 1]
            except Exception as e:
                print(f"ERROR occurred: {e}, {e.__class__.__name__}")
                traceback.print_exc()
                break

        if self.serial is not None:
            print(f"Closing serial port: {self.serial.port}")
            self.serial.close()
            print(f"Serial port {self.serial.port} closed successfully.")

        # self.running was set to False or the stop event was set or connect failed
        print("break...")
        if self.stop_event and not self.stop_event.is_set():
            print("break...set stop event")
            self.stop_event.set()
        for outlet in self._o:
            print(f"break...join {outlet.name}")
            outlet.join()


    def stop(self):
        self.running = False
        self.is_connected = False


def main():
    parser = ArgumentParser(description='Serial port repeater.', formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--port', required=True, help='serial port to listen on')
    parser.add_argument('--baudrate', default=9600, type=int, help='baud rate for incoming port. Default=9600')
    parser.add_argument('--outlet', action='append', required=True, help='Specify serial/tcp e.g. serial,COM7 or tcp,host,port')
    parser.add_argument('--gui', action='store_true', help='Get gui and systray too!')
    args = parser.parse_args()
    print(f"port {args.port}")
    print(f"outlets: {len(args.outlet)}")
    print(f"gui? {str(args.gui)}")
    repeater = SerialRepeater(port=args.port, baudrate=args.baudrate, outlets=args.outlet)

    try:
        repeater.start()    # this starts the repeater thread, which will start each of the outlet threads
    except Exception as e:
        print(f"Main Error occurred: {e}, {e.__class__.__name__}")
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



if __name__ == "__main__":
    main()
