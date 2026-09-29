from threading import Thread
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from serial_repeater import SerialRepeater
from platformdirs import PlatformDirs
import serial.tools.list_ports as list_ports
import PySimpleGUI as sg
import logging
import configparser
logger = logging.getLogger("shlub")
icon = b'iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAFmklEQVR4nO1bXWgUVxT+7p3Z3dAmaH6gEWwTo6VVo0QTyJM+RAQRNaL1UdpAX0RRFNEHS9VC34J/+JjSQp5Exd8HQUXiixCJS3GrjSaxiQ8KTbIrbkp2d/becu7MmHW72T8nZmenH0w2M3PvnfnOveec787MBf6Ht8FynGPAcbgfJ+mPtLZ8cJwDHOUFbvHKPQKYZSkeCASapKzRgbgEAnAfYgD8jLFJIxaLDVu8bH4KaQYgC/0kfL4vVyeT3/8qZeNKQGjmOZnNXUoUzCLKk4z99Yem/fJdIvHsMfAjB04KVeL9CpK3tjItGPy5X4hvWoCwBBhLM5qLYN+3lEA14/xicM2aH9oHBmQSYMoAekppTgdDoUCjlI3NQEQA05bvuJF8qhGEBCJSyiWrQqHA5wAbsYiJlKBgRnspP62wep1bvwzgLt5sDsSHW/xm+PIMJnNzd+eAimPv8ePwODg8Dn0uGiWPywaKyWVtAJmTIStXA0hFrrrap3o5fSTYx8JhQ5VljM37aNCdaMQmqusMFy8ux/r1CyAEwNMijBASnDPcv/8Gu3Y9hWGYdefTCLoTjRAJIQQaGj5BZ2dtzvJUpqGhAkND/4Bzys0oDxfw+Rjical+s7lAImGWKQXoTjZGBGnY28QzZQOlK3npZAIOFyNXui1bA3CS+Cnp1t4vqi24DERWCDON1tX51S/tF2sEjnkCpcxCN7+fK7IdHTV49GgtHjxYjWBwLTZsqCnaCDrmCa9fx2EYsQL6gMglsWhRFa5eXYFDh0Zw48Y4tm6tw+XLK9DWFsTwMKVVTekNRw3ALMN+aOSeyQ4Mp083IRIx8laDVNcwkmhvX4ALF/5GT88YNK0CPT2j6OhYiK6uz3Ds2BA0jQyQ/z3xXBfVNLpBqTb634nIOxcotnP0XI0mkwlUVppPhKPR2Ad5jS2EyJgHD45gfDxalAsMDrahv/8LXL8+jm3bGrF5c41yAcYK633MxiZV2589+xU2bqxW+3fuRLB//5D6X6Y8JCZhIwRTIyRf1Nf7EYkElBTO96YpyL16NY3Ozifo7l6CI0cW4+1bgR07nmBoaAqc6wX5/6wGoAsZhoHz55ehpaUSW7Y8Vsd7e5fj3Lll2LMnZFVNvZjAxASlpfxgGFJtnFMay7cWlddx794kWlsjKg2Oj8fVtYshn9EAfj8NdYHKSj82bVqIdetCGBubUud27nyKhw9b8Pz5UiQS4l0AoxGQTErVq9lksBMwZ5S6ciMiT/fAWHHkXSmEnIaefiAeJ9/niEbjuHUrjEuXvsbu3X++c4ErVyZw6tRwRheor6/E0aOL1V6m2aCzSpC/cwEpk865AIEaomG1b98wzpxZhps3V6njt2+HceDAMHy+igxBUKC21od8Yas7k1B+dahsPJ5QSrC7uwlVVdRRAocPj+Du3UnngqCU5kbz9r17B2dJgzLNAFLFgbJSgkzN3X2IRmnIkSjyqcaLFR2lqAT13ELIfHhJKKSHy0IJ2nDq6Y1rlODHQEkrwY+BUlGCHC6DrQTJJUzylEo9pgSFRdYOzsWSd60BnAzOOhyE+YZoRkilwz5GZUrlwYruZGOkHP1+lvWlCIHKUNmyMYBU+Z1jdHQa165N5Hw52tf3RpWlOvP9hkh3opHUd37btz9FdbXurdfjBJOIyTgcTiA7zM+Q55v8HH4ikz3ClQLxOf5EBq4Bh8fB4XFweBwcHgeHx8HhcXB4HDzDMfq23kWZvGCwWYTQSfMsm5qmR0yApIltgavNShFqiYA1QZfS5DfDV08pSYR5czN7GQy+eCxl25qZ6Yvr1wwBWMgYe/F7c3Ps5cCAVMuD8F8pfAIDAyzh8/V+C/h/k7JhJSDLYNUYSzLWF9K03i7iB5zg+awbZIFAYGm5rxucBd5eOWrDy2uH4Rn8C5q3x8IuMQ1DAAAAAElFTkSuQmCC'
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