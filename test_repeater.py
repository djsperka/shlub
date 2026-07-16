from serial_repeater import SerialRepeater
from threading import Event, Thread
from time import sleep as sleep
from serial import Serial
import logging
from local_server import SingleClientServer

logger = logging.getLogger(__name__)


import sys
if sys.platform=="linux":
    GOOD_SERIAL_PORT="/home/dan/mydev/ttyV0"
    PAIR1_IN="/home/dan/mydev/ttyV0"
    PAIR1_OUT="/home/dan/mydev/ttyV1"
    PAIR2_IN="/home/dan/mydev/ttyV2"
    PAIR2_OUT="/home/dan/mydev/ttyV3"
    BAD_SERIAL_PORT="COM6"
    TCP_HOST = "127.0.0.1"
    TCP_PORT = 9990
elif sys.platform=="win32":
    GOOD_SERIAL_PORT="COM7"
    PAIR1_IN="COM6"
    PAIR1_OUT="COM7"
    PAIR2_IN="COM8"
    PAIR2_OUT="COM9"
    BAD_SERIAL_PORT="COM99"
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
    assert(repeater.all_outlets_connected)

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

    # CONNECT - shouldn't do anything
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
    assert(repeater.all_outlets_connected)

    print("send whatever")
    source.send(b"whatever;")
    sleep(1)
    print("send disconnect")
    source.send(b"disconnect;")
    sleep(2)
    assert(repeater.state == SerialRepeater.States.NOT_CONNECTED)


    repeater.stop()
    sleep(1)
    assert(repeater.state == SerialRepeater.States.DONE)

    repeater.join()
    downstream_tcp.stop()
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


def test_repeater_with_two_outlets():
    outlets = [f"tcp,{TCP_HOST},{TCP_PORT}",f"serial,{PAIR2_IN}"]
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
    sleep(5)
    assert(repeater.state == SerialRepeater.States.NOT_CONNECTED)


    repeater.stop()
    sleep(1)
    assert(repeater.state == SerialRepeater.States.DONE)

    logger.info("repeater.join")
    repeater.join()
    downstream_tcp.stop()
    logger.info("downstream join")
    downstream_tcp.join()




class RepeaterSource:
    def __init__(self, port):
        self.serial = Serial()
        self.serial.port = port
        self.serial.baudrate = 115200
        self.serial.open()

    def send(self, msg):
        i = self.serial.write(msg)
        logger.info(f"RepeaterSource wrote {i}")


