import serial
import logging

logger = logging.getLogger(__name__)

class SerialInputQueue:
    def __init__(self, ser:serial.Serial, expected:str=';'):
        self.ser = ser
        self.bexpected = bytearray(expected, 'utf-8')
        self.buffer = bytearray()

    def check(self)->bool:
        #if self.ser.in_waiting:
            #logger.debug(f"in waiting {self.ser.in_waiting}")
        data = self.ser.read_until(self.bexpected)
        if data:
            #logger.debug(f"siq.check read {data}")
            self.buffer.extend(data)
        return b';' in self.buffer
    
    def next(self)->bytes:
        try:
            terminator_index = self.buffer.index(self.bexpected)
        except ValueError:
            return b''
        msg = self.buffer[:terminator_index + 1]
        del self.buffer[:terminator_index + 1]
        return msg


