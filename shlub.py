from threading import Thread
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from serial_repeater import SerialRepeater
from pathlib import Path
import serial.tools.list_ports as list_ports
import PySimpleGUI as sg
import logging
import tomlkit
from tomlkit.items import Array
logger = logging.getLogger("shlub")

CONFIG_FILE = Path.home() / ".shlub" / "config.toml"
DEFAULTS = {"in_serial_port": "COM7",
            "outlets": ["serial,COM8", "tcp,128.120.140.96,9292"]}
icon = b'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'
def _outlets_array(outlets) -> Array:
    arr = tomlkit.array()
    arr.extend(outlets)
    arr.multiline(True)
    return arr

def save_config(doc: tomlkit.TOMLDocument):
    CONFIG_FILE.write_text(tomlkit.dumps(doc), encoding="utf-8")

def load_config() -> tomlkit.TOMLDocument:
    """Load ~/.shlub/config.toml, creating it with defaults if it doesn't exist."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        logger.info(f"Creating initial config file {CONFIG_FILE}")
        doc = tomlkit.document()
        doc.add(tomlkit.comment("SHLUB configuration"))
        doc.add(tomlkit.comment("outlets: 'serial,PORT' or 'tcp,HOST,PORT'"))
        doc["in_serial_port"] = DEFAULTS["in_serial_port"]
        doc["outlets"] = _outlets_array(DEFAULTS["outlets"])
        save_config(doc)
        return doc

    logger.info(f"Loading config file {CONFIG_FILE}")
    doc = tomlkit.parse(CONFIG_FILE.read_text(encoding="utf-8"))
    # fill in anything missing from a partial file
    if "in_serial_port" not in doc:
        doc["in_serial_port"] = DEFAULTS["in_serial_port"]
    if "outlets" not in doc:
        doc["outlets"] = _outlets_array(DEFAULTS["outlets"])
    return doc

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
    # parser arguments override and are saved back into the config file
    config = load_config()
    if args.port:
        config["in_serial_port"] = args.port
    if args.outlet:
        config["outlets"] = _outlets_array(args.outlet)
    if args.port or args.outlet:
        logger.info(f"Saving command line settings to {CONFIG_FILE}")
        save_config(config)

    # convert tomlkit items to plain python types for the repeater
    outlets = [str(o) for o in config["outlets"] if str(o)]
    repeater = SerialRepeater(port=str(config["in_serial_port"]), outlets=outlets)
    gui = Thread(target=loop, args=(repeater,))

    gui.start()
    repeater.start()

    repeater.join()
    gui.join()

if __name__ == "__main__":
    main()

# python shlub.py --port COM7 --outlet serial,COM8 --outlet tcp,128.120.140.66,9292