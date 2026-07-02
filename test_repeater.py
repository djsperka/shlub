from serial_repeater import SerialRepeater
from threading import Event, Thread
from time import sleep as sleep
from serial import Serial
import logging
from local_server import SingleClientServer

logger = logging.getLogger(__name__)

# This is good/bad on linux, not in lab.
GOOD_SERIAL_PORT="/home/dan/mydev/ttyV0"
ANOTHER_GOOD_SERIAL_PORT="/home/dan/mydev/ttyV1"
PAIR1_IN="/home/dan/mydev/ttyV0"
PAIR1_OUT="/home/dan/mydev/ttyV1"
PAIR2_IN="/home/dan/mydev/ttyV2"
PAIR2_OUT="/home/dan/mydev/ttyV3"
BAD_SERIAL_PORT="COM6"

TCP_HOST = "127.0.0.1"
TCP_PORT = 9990

def test_empty_repeater():
    repeater = SerialRepeater(GOOD_SERIAL_PORT)
    repeater.start()
    sleep(1)
    assert(repeater.state == SerialRepeater.States.NOT_CONNECTED)
    repeater.stop()
    sleep(1)
    assert(not repeater.is_alive())
    repeater.join()

def test_repeater_with_serial():
    outlets = [f"serial,{PAIR2_IN}"]
    source = RepeaterSource(PAIR1_IN)
    repeater = SerialRepeater(PAIR1_OUT, outlets=outlets)
    repeater.start()
    sleep(1)
    assert(repeater.state == SerialRepeater.States.NOT_CONNECTED)

    # CONNECT
    source.send(b'connect;')
    sleep(2)
    assert(repeater.state == SerialRepeater.States.CONNECTED)

    print("send whatever")
    source.send(b"whatever;")
    print("send disconnect")
    source.send(b"disconnect;")
    sleep(2)
    assert(repeater.state == SerialRepeater.States.NOT_CONNECTED)


    repeater.stop()
    sleep(1)
    assert(repeater.state == SerialRepeater.States.DONE)

    repeater.join()



def test_repeater_with_bad_serial():
    outlets = [f"serial,{BAD_SERIAL_PORT}"]
    source = RepeaterSource(PAIR1_IN)
    repeater = SerialRepeater(PAIR1_OUT, outlets=outlets)
    repeater.start()
    sleep(1)
    assert(repeater.state == SerialRepeater.States.NOT_CONNECTED)

    # CONNECT
    source.send(b'connect;')
    sleep(2)
    assert(repeater.state == SerialRepeater.States.NOT_CONNECTED)

    repeater.stop()
    sleep(1)
    assert(repeater.state == SerialRepeater.States.DONE)

    repeater.join()


def test_repeater_with_tcp():
    outlets = [f"tcp,{TCP_HOST},{TCP_PORT}"]
    source = RepeaterSource(PAIR1_IN)
    downstream_tcp = SingleClientServer(host=TCP_HOST, port=TCP_PORT)
    downstream_tcp.start()

    repeater = SerialRepeater(PAIR1_OUT, outlets=outlets)
    repeater.start()
    sleep(1)
    assert(repeater.state == SerialRepeater.States.NOT_CONNECTED)

    # CONNECT
    source.send(b'connect;')
    sleep(2)
    assert(repeater.state == SerialRepeater.States.CONNECTED)

    print("send whatever")
    source.send(b"whatever;")
    print("send disconnect")
    source.send(b"disconnect;")
    sleep(2)
    assert(repeater.state == SerialRepeater.States.NOT_CONNECTED)


    repeater.stop()
    sleep(1)
    assert(repeater.state == SerialRepeater.States.DONE)

    repeater.join()
    downstream_tcp.join()

def test_repeater_with_bad_tcp():
    outlets = [f"tcp,{TCP_HOST},{TCP_PORT}"]
    source = RepeaterSource(PAIR1_IN)
    # comment these out - nothing to connect to!
    # downstream_tcp = SingleClientServer(host=TCP_HOST, port=TCP_PORT)
    # downstream_tcp.start()

    repeater = SerialRepeater(PAIR1_OUT, outlets=outlets)
    repeater.start()
    sleep(1)
    assert(repeater.state == SerialRepeater.States.NOT_CONNECTED)

    # CONNECT
    source.send(b'connect;')
    sleep(2)
    assert(repeater.state == SerialRepeater.States.NOT_CONNECTED)

    print("send whatever")
    source.send(b"whatever;")
    print("send disconnect")
    source.send(b"disconnect;")
    sleep(2)
    assert(repeater.state == SerialRepeater.States.NOT_CONNECTED)


    repeater.stop()
    sleep(1)
    assert(repeater.state == SerialRepeater.States.DONE)

    repeater.join()
    # downstream_tcp.join()s


class RepeaterSource:
    def __init__(self, port):
        self.serial = Serial()
        self.serial.port = port
        self.serial.baudrate = 115200
        self.serial.open()

    def send(self, msg):
        i = self.serial.write(msg)
        logger.info(f"RepeaterSource wrote {i}")


