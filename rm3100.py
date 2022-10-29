# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2022 Phil Underwood for Underwood Underground
#
# SPDX-License-Identifier: MIT
"""
`rm3100`
================================================================================

Driver for the RM3100 magnetometer by PNI Sensor Corporation


* Author(s): Phil Underwood

Implementation Notes
--------------------

**Hardware:**

* `RM3100 (PNI Sensor Coroporation) <https://www.pnicorp.com/rm3100/>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/furbrain/CircuitPython_RM3100.git"

import time
import struct
import math
from typing import Optional, Tuple

from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_bus_device.spi_device import SPIDevice
from busio import SPI, I2C
from microcontroller import Pin
from micropython import const

# define register addresses
_POLL = const(0x0)
_CMM = const(0x01) # continuous mode
_CCX = const(0x04) # cycle counts
_TMRC = const(0x0B) # timer
_MX = const(0x24) # measurements
_STATUS = const(0x34)
_CYCLE_DURATION = const(0.000036)


class _RM3100:
    """Communicate with RM3100 magnetometers, using SPI or I2C interfaces"""

    def __init__(self, cycle_count: int = 200, int_pin: Optional[Pin] = None):
        """
        Parameters
        ----------
        cycle_count: int
            how many cycles to use when making measurements
        int_pin: Pin | None
            the interrupt pin (connected to DRDY on RM3100)
            leave as None if not used (the STATUS register will be polled instead)
        """
        self.cycle_count = cycle_count
        self.int_pin = int_pin
        # set cycle count
        values = struct.pack(">HHH",self.cycle_count,self.cycle_count,self.cycle_count)
        self._write_reg(_CCX, values)
        self.continuous = False

    def get_reading(self) -> Tuple[int]:
        #FIXME - use DRDY if set
        while not self._read_reg(_STATUS):
            pass
        results = self._read_multiple(_MX, 9)
        return tuple(int.from_bytes(results[x:x+3], "big", signed=True) for x in range(0,9,3))

    def get_single_reading(self) -> Tuple[int]:
        # start read
        self._write_reg(_POLL, bytearray([0x70]))
        time.sleep(_CYCLE_DURATION*self.cycle_count)
        return self.get_reading()

    def start_continuous_reading(self, frequency:float=300):
        # write frequency
        exponent = round(math.log2(600/frequency))
        exponent = min(13,exponent)
        value = 0x92+int(exponent)
        self._write_reg(_TMRC, bytearray([value]))
        # start continuous reading, using all three axes
        self._write_reg(_CMM, bytearray([0x71]))
        self.continuous = True

    def get_continuous_reading(self):
        if not self.continuous:
            raise ValueError("RM3100 not in continuous mode")
        return self.get_reading()

    def stop(self):
        self._write_reg(_CMM,bytearray([0x70]))
        self.continuous = False

    def _write_reg(self, addr:int, data: bytes):
        raise NotImplementedError

    def _read_multiple(self, addr:int, size: int):
        raise NotImplementedError

    def _read_reg(self, addr: int) -> int:
        result = self._read_multiple(addr, 1)
        return result[0]


class RM3100_I2C(_RM3100):
    def __init__(self, bus: I2C, i2c_address: int = 0x20, cycle_count: int = 200, int_pin: Optional[Pin] = None):
        """
        Parameters
        ----------
        bus: I2C
            I2C bus to use to communicate with the RM3100
        i2c_address: int
            I2C address of RM3100, 0x20 - 0x23 depending on pins SA0 and SA1
        cycle_count: int
            how many cycles to use when making measurements
        int_pin: Pin | None
            the interrupt pin (connected to DRDY on RM3100)
            leave as None if not used (the STATUS register will be polled instead)
        """
        self.device: I2CDevice = I2CDevice(bus, i2c_address)
        super().__init__(cycle_count, int_pin)

    def _write_reg(self, addr: int, data: bytes):
        data = bytes([addr]) + data
        self.device.write(data)

    def _read_multiple(self, addr:int, size:int) -> bytearray:
        result = bytearray(size)
        self.device.write_then_readinto(bytes([addr]), result)
        return result


class RM3100_SPI(_RM3100):
    def __init__(self, bus: SPI, chip_select: Pin, cycle_count: int = 200, int_pin: Optional[Pin] = None):
        """
        Parameters
        ----------
        bus: I2C
            I2C bus to use to communicate with the RM3100
        chip_select: Pin
            pin to signal to RM3100 to listen to SPI bus
        cycle_count: int
            how many cycles to use when making measurements
        int_pin: Pin | None
            the interrupt pin (connected to DRDY on RM3100)
            leave as None if not used (the STATUS register will be polled instead)
        """
        self.device = SPIDevice(bus, chip_select)
        super().__init__(cycle_count, int_pin)

    def _write_reg(self, addr: int, data: bytes):
        data = bytes([addr]) + data
        with self.device as spi:
            spi.write(data)

    def _read_multiple(self, addr:int, size:int) -> bytearray:
        result = bytearray(size+1)
        output = bytearray(size+1)
        output[0] = addr | 0x80 # set upper bit to signal a read
        with self.device as spi:
            spi.write_readinto(output,result)
        return result[1:] # ignore first byte read as it is always blank
