from threading import Thread
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from serial_repeater import SerialRepeater
from platformdirs import PlatformDirs
import serial.tools.list_ports as list_ports
import PySimpleGUI as sg
import logging
import configparser
logger = logging.getLogger("shlub")

def load_config():
    config = configparser.ConfigParser()
    config['DEFAULT'] = {'in_serial_port': 'COM7',
                         'out_serial_port': 'COM8',
                         'out_tcp_addr': '128.120.140.66',
                         'out_tcp_port': '9292'}

    # Path for config file
    config_path = PlatformDirs("SHLUB", appauthor=False).user_config_path
    config_path.mkdir(exist_ok=True, parents=True)
    config_file = config_path / "shlub.ini"

    # create config file if it doesn't exist
    if not config_file.exists():
        logger.info(f"Creating initial config file {str(config_file)}")
        with config_file.open(mode="w") as fp:
            config.write(fp)

    # now load the config
    config = configparser.ConfigParser()
    config.read(str(config_file))
    return config

class OutputHandler(logging.Handler):

    def __init__(self, window: sg.Window, elekey: str):
        super().__init__()
        self.window = window
        self.key = elekey

    def emit(self, record):
        msg = self.format(record)
        self.window[self.key].print(msg)
        self.window.refresh()

def loop(repeater:SerialRepeater, level=logging.INFO):

    ports = sorted([a for (a,b,c) in list_ports.comports()])

    # assumes that a single serial output and single tcp outlet exist. Program doesn't require that - any combination is allowed - 
    # but our usage of it involves two outlets: 
    # serial,COMX - serial out - this is for fixstim (should be same as arg passed to fixstim)
    # tcp,ip,port - tcp output - this is the calibrator on the tracker machine

    fixstim_port = ""
    tcp_addr = ""
    tcp_port = ""

    for o in repeater.outlets:
        l = o.split(",")
        print(l[0])
        if l[0]=="serial":
            fixstim_port = l[1]
            print(f"fixstim port {fixstim_port}")
        elif l[0]=="tcp":
            tcp_addr = l[1]
            tcp_port = l[2]
            print(f"tcp {tcp_addr}:{tcp_port}")

    NAME_SIZE = 23
    def name(name):
        dots = NAME_SIZE-len(name)-2
        return sg.Text(name + ' ' + '•'*dots, size=(NAME_SIZE,1), justification='r',pad=(0,0), font='Courier 10')

    # window
    layout = [
        [name('Input port'), sg.Combo(ports, default_value=repeater.port, s=(15,22), enable_events=True, readonly=True, k='-INCOMPORT-')],
        [name('Serial outlet port'), sg.Combo(ports, default_value=fixstim_port, s=(15,22), enable_events=True, readonly=True, k='-OUTCOMPORT-')],
        [name('Calibrator ip'), sg.Input(s=15, default_text=tcp_addr, k='-TCPADDR-')],
        [name('Calibrator port'), sg.Input(s=5, default_text=tcp_port, k='-TCPPORT-')],
        [sg.Multiline(default_text="", size=(60, 15), disabled=True, autoscroll=True, key="-LOG-")]
        ]
    window = sg.Window("Test", layout, finalize=True)

    # logging stuff
    handler = OutputHandler(window, "-LOG-")
    formatter = logging.Formatter('%(asctime)s:%(module)s:%(levelname)s - %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logging.getLogger().setLevel(level)
    logging.getLogger().addHandler(handler)

    while True:
        event, values = window.read(timeout=20)

        if event==sg.WIN_CLOSED:
            window.close()
            repeater.stop()
            break

def main():
    parser = ArgumentParser(description='Serial port repeater.', formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--port', required=True, help='serial port to listen on')
    parser.add_argument('--baudrate', default=9600, type=int, help='baud rate for incoming port. Default=9600')
    parser.add_argument('--outlet', action='append', required=True, help='Specify serial/tcp e.g. serial,COM7 or tcp,host,port')
    parser.add_argument('--gui', action='store_true', help='Get gui and systray too!')
    args = parser.parse_args()


    repeater = SerialRepeater(port=args.port, baudrate=args.baudrate, outlets=args.outlet)
    gui = Thread(target=loop, args=(repeater,))

    gui.start()
    repeater.start()

    repeater.join()
    gui.join()

if __name__ == "__main__":
    main()

# python shlub.py --port COM7 --outlet serial,COM8 --outlet tcp,128.120.140.66,9292