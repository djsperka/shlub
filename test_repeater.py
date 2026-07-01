from serial_repeater import SerialRepeater
from threading import Event, Thread
from time import sleep as sleep

# This is good/bad on linux, not in lab.
GOOD_SERIAL_PORT="/home/dan/mydev/ttyV0"
BAD_SERIAL_PORT="COM6"

TCP_HOST = "127.0.0.1"
TCP_PORT = 9990

def test_empty_repeater():
    repeater = SerialRepeater(GOOD_SERIAL_PORT)
    repeater.start()
    sleep(1)
    assert(repeater.is_alive())
    assert(repeater.running)

    repeater.stop()
    sleep(1)
    assert(not repeater.running)
    assert(not repeater.is_alive())

    repeater.join()
