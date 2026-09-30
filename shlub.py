from threading import Thread
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from serial_repeater import SerialRepeater
from platformdirs import PlatformDirs
import serial.tools.list_ports as list_ports
import PySimpleGUI as sg
import logging
import configparser
logger = logging.getLogger("shlub")
icon = b'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'
def load_config():
    config = configparser.ConfigParser()
    config['DEFAULT'] = {'in_serial_port': 'COM7',
                         'outlet0': 'serial,COM8',
                         'outlet1': 'tcp,128.120.140.66,9292'}

    # Path for config file
    config_path = PlatformDirs("shlub", appauthor=False).user_config_path
    config_path.mkdir(exist_ok=True, parents=True)
    config_file = config_path / "shlub.ini"

    # create config file if it doesn't exist
    if not config_file.exists():
        logger.info(f"Creating initial config file {str(config_file)}")
        with config_file.open(mode="w") as fp:
            config.write(fp)

    # now load the config
    logger.info(f"Loading config file {str(config_file)}")
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

    NAME_SIZE = 23
    def name(name):
        dots = NAME_SIZE-len(name)-2
        return sg.Text(name + ' ' + '•'*dots, size=(NAME_SIZE,1), justification='r',pad=(0,0), font='Courier 10')
    VALUE_SIZE = 23
    def value(v):
        return sg.Text(v, size=(VALUE_SIZE,1), justification='l', pad=(0,0), font='Courier 10')


    # window layout
    layout = [[name('Input port'), value(repeater.port)]]
    for (i,outlet) in enumerate(repeater.outlets):
        layout.append([name(f"outlet{i}"), value(repeater.outlets[i])])
    layout.append([sg.Multiline(default_text="", size=(80, 15), disabled=True, autoscroll=True, key="-LOG-")])
    window = sg.Window("shlub", layout, finalize=True, icon=icon)

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
    parser.add_argument('--port', type=str, default='', help='serial port to listen on')
    parser.add_argument('--outlet', action='append', help='Specify serial/tcp e.g. serial,COM7 or tcp,host,port')
    args = parser.parse_args()

    # load config first. 
    # parser arguments override (and are saved into config later)
    config = load_config()
    if args.port:
        config['DEFAULT']['in_serial_port'] = args.port
    if args.outlet and len(args.outlet):
        for (i,outlet) in enumerate(args.outlet):
            okey=f"outlet{i}"
            config['DEFAULT'][okey] = outlet
        # remove any config values greater than args.outlet.size()
        for i in range(len(args.outlet),10):
            okey=f"outlet{i}"
            if config.has_option('DEFAULT', okey):
                config['DEFAULT'][okey] = ''

    # make a list of the outlets
    outlets = []
    for i in range(10):
        okey=f"outlet{i}"
        if config.has_option('DEFAULT',okey) and config['DEFAULT'][okey]:
            outlets.append(config['DEFAULT'][okey])

    repeater = SerialRepeater(port=config['DEFAULT']['in_serial_port'], outlets=outlets)
    gui = Thread(target=loop, args=(repeater,))

    gui.start()
    repeater.start()

    repeater.join()
    gui.join()

if __name__ == "__main__":
    main()

# python shlub.py --port COM7 --outlet serial,COM8 --outlet tcp,128.120.140.66,9292