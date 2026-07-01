from outlet import Outlet, SerialOutlet, TCPClientOutlet
from threading import Event, Thread
from time import sleep as sleep

def main():

    connect_event = Event()
    stop_event = Event()

    outlet = SerialOutlet("COM6", connect_event=connect_event, stop_event=stop_event)
    outlet.start()
    connect_event.set()
    sleep(1)
    stop_event.set()
    outlet.join()

if __name__ == '__main__':
    main()
