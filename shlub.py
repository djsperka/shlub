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