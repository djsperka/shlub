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