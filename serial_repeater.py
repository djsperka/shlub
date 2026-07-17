from serial import Serial
from threading import Thread, Event
from time import sleep as sleep
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from outlet import Outlet, SerialOutlet, TCPClientOutlet
from typing import List
from enum import Enum
import traceback
from serial_input_queue import SerialInputQueue
import logging
import PySimpleGUI as sg

A_WINK = 0.1    # Time to sleep
logger = logging.getLogger(__name__)

class SerialRepeater(Thread):
    """This class will accept input via a serial port, and send it out to any number of serial and/or tcp/ip ports.
    It runs as a state machine, which can be in one of three states, NOT_CONNECTED, CONNECTING, CONNECT_FAIL, and CONNECTED.

    Args:
        Thread (_type_): _description_
    """ 

    class States(Enum):
        NOT_STARTED=1
        NOT_CONNECTED=2
        CONNECTING=3
        CONNECT_FAIL=4
        CONNECTED=5
        DISCONNECTING=6
        QUITTING=7
        DONE=99

    def __init__(self, port, baudrate=9600, outlets:List[str] = [], timeout=0, autoconnect = False):
        super().__init__()
        self.port:str = port
        self.baudrate:int = baudrate
        self.timeout:float = timeout
        self.serial:None|Serial = None
        self.connect_event:Event|None = None
        self.disconnect_event:Event|None = None
        self.outlets:List[str] = outlets
        self.autoconnect = autoconnect
        self._o:List[Outlet] = []
        self.state:SerialRepeater.States=SerialRepeater.States.NOT_STARTED  

    @property
    def all_outlets_connected(self):
        return self.state == SerialRepeater.States.CONNECTED

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
        logger.info("connect_all()")

        # new events
        self.connect_event = Event()
        self.disconnect_event = Event()

        bFail = False
        for outletstring in self.outlets:
            logger.info(f"Adding outlet with config: {outletstring}")
            l = outletstring.split(",")
            if len(l) > 0:
                if l[0].lower() == "serial" and len(l)==2:
                    o = SerialOutlet(l[1], connect_event=self.connect_event, disconnect_event=self.disconnect_event)
                    self._o.append(o)
                elif l[0].lower() == "tcp" and len(l)==3:
                    o = TCPClientOutlet(l[1], int(l[2]), connect_event=self.connect_event, disconnect_event=self.disconnect_event)
                    self._o.append(o)
                else:
                    logger.warning(f"Cannot open outlet with argument {outletstring}")
                    bFail = True

        # Check that all threads were created. If not, bail.
        if bFail:
            return False

        # Now start each thread and set connect event
        logger.info("Starting threads and setting connect event...")
        for o in self._o:
            o.start()
        self.connect_event.set()

        # If outlet could not be connected, the outlet thread should end. 
        # Wait a couple of seconds for outlets to connect (only tcp outlet might take time)
        sleep(1)
        waitready = True
        for outlet in self._o:
            logger.info(f"connect_all: {outlet.name} alive {str(outlet.is_alive())} connected {str(outlet.connected)}")
            if not outlet.connected:
                waitready = False
        return waitready and len(self._o)==len(self.outlets)

    def run(self):
        try:
            logger.info("starting repeater...")
            self.serial = Serial(self.port, self.baudrate, timeout=self.timeout)
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
        except Exception as e:
            logger.error(f"Error connecting repeater port {self.port}: ")
            traceback.print_exc()
            return

        # Serial input is open. Start state machine here at state NOT_CONNECTED
        self.state = SerialRepeater.States.NOT_CONNECTED
        siq = SerialInputQueue(self.serial, expected=';')
        while not self.state==SerialRepeater.States.DONE:

            if self.state==SerialRepeater.States.NOT_CONNECTED:
                while self.state==SerialRepeater.States.NOT_CONNECTED and siq.check():
                    msg = siq.next()
                    if msg.lower() == b'connect;':
                        if self.connect_all():
                            self.state = SerialRepeater.States.CONNECTING
                            logger.info("connect_all started connections...")
                        else:
                            logger.info("connect_all connect FAIL!")
                            self.disconnect_all()
                            self.state =SerialRepeater.States.DISCONNECTING
                    else:
                        logger.info(f"SerialRepeater - expecting 'connect;', discarding input: {msg}")
            elif self.state==SerialRepeater.States.CONNECTING:
                # Source - https://stackoverflow.com/a/10666320
                # Posted by Gareth Latty, modified by community. See post 'Timeline' for change history
                # Retrieved 2026-07-16, License - CC BY-SA 4.0
                if all(outlet.connected for outlet in self._o) and len(self._o) == len(self.outlets):
                    logger.info("all outlets connected.")
                    self.state = SerialRepeater.States.CONNECTED
                else:
                    # some are not connected. That means they failed - as the outlet should end
                    # if connect() failed. Also assuming that connect() has been attempted. Now
                    # that the thread/connection is made when the Outlet class is instantiated, 
                    # we are assured that the attempt was made, and we aren't waiting for it to be
                    # completed (it blocks/timeout)
                    self.disconnect_all()
                    self.state =SerialRepeater.States.DISCONNECTING

            elif self.state==SerialRepeater.States.CONNECT_FAIL:
                # an attempt to connect failed. Stop any threads that started and clear out the contents of self._o
                for outlet in self._o:                    
                    outlet.join()
                self._o.clear()
                self.state = SerialRepeater.States.NOT_CONNECTED
            elif self.state==SerialRepeater.States.CONNECTED:
                if siq.check():
                    msg = siq.next()
                    if msg.lower() == b'disconnect;':
                        logger.info("repeater: disconnect; received, disconnecting...")
                        self.disconnect_all()
                        self.state = SerialRepeater.States.DISCONNECTING
                    else:
                        for outlet in self._o:
                            outlet.mailbox.put(msg)
            elif self.state in [SerialRepeater.States.DISCONNECTING, SerialRepeater.States.QUITTING]:
                # we are waiting for each of the outlet threads to disconnect and finish
                #logger.info("disconnecting")
                for outlet in self._o:                    
                    outlet.join()
                self._o.clear()
                if self.state==SerialRepeater.States.DISCONNECTING:
                    self.state = SerialRepeater.States.NOT_CONNECTED
                    logger.info("to NOT_CONNECTED")
                else:
                    self.state = SerialRepeater.States.DONE
                    logger.info("to DONE")
            else:
                logger.error(f"Unknown state: {str(self.state)}")
                self._state = SerialRepeater.States.DONE
                        

    def disconnect_all(self):
        if self.disconnect_event:
            self.disconnect_event.set()


    def stop(self):
        if self.disconnect_event:
            self.disconnect_event.set()
        self.state = SerialRepeater.States.QUITTING


def main():
    logging.basicConfig(level=logging.NOTSET)
    parser = ArgumentParser(description='Serial port repeater.', formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--port', required=True, help='serial port to listen on')
    parser.add_argument('--baudrate', default=9600, type=int, help='baud rate for incoming port. Default=9600')
    parser.add_argument('--outlet', action='append', required=True, help='Specify serial/tcp e.g. serial,COM7 or tcp,host,port')
    parser.add_argument('--gui', action='store_true', help='Get gui and systray too!')
    args = parser.parse_args()
    repeater = SerialRepeater(port=args.port, baudrate=args.baudrate, outlets=args.outlet)
    repeater.start()
    # layout = [[sg.Button('Start'), sg.Button('Stop')]]
    # window = sg.Window('SHLUB', layout)
    # repeater_started = False
    # while True:
    
    #     event, values = window.read()
    
    #     if event in (sg.WIN_CLOSED, 'Cancel'):
    #         break
    #     elif event == 'Start': 
    #         if not repeater_started:
    #             logger.info("call repeater.start()")
    #             repeater.start()
    #             repeater_started = True
    #     elif event == 'Stop':
    #         logger.info("call repeater.stop()")
    #         repeater_started = False
    #         repeater.stop()
    
    # window.close()

    # if repeater_started:
    #     logger.info("loop done - join repeater")
    #     repeater.join()
    repeater.join()


if __name__ == "__main__":
    main()
