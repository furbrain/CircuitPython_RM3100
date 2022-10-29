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

import digitalio
from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_bus_device.spi_device import SPIDevice
from micropython import const

try:  # ignore runtime errors from typing
    from typing import Optional, Tuple
    from busio import SPI, I2C
    from microcontroller import Pin
except ImportError:
    pass


# define register addresses
_POLL = const(0x0)
_CMM = const(0x01)  # continuous mode
_CCX = const(0x04)  # cycle counts
_TMRC = const(0x0B)  # timer
_MX = const(0x24)  # measurements
_STATUS = const(0x34)
_CYCLE_DURATION = 0.000036


class _RM3100:
    """
    Communicate with RM3100 magnetometers, using SPI or I2C interfaces
    This is an abstract parent class, please use RM3100_I2C or RM3100_SPI
    """

    def __init__(self, cycle_count: int = 200, int_pin: Optional[Pin] = None):
        self.cycle_count = cycle_count
        self.int_pin = int_pin
        # set cycle count
        values = struct.pack(
            ">HHH", self.cycle_count, self.cycle_count, self.cycle_count
        )
        self._write_reg(_CCX, values)
        self.continuous = False

    def wait_for_fresh_reading(self):
        """
        Wait until there is a new reading available.
        """
        if self.int_pin is not None:
            while self.int_pin.value == Pin.LOW:
                time.sleep(0.01)
        else:
            while not self._read_reg(_STATUS):
                pass

    def get_last_reading(self) -> Tuple[int, int, int]:
        """
        Get the most recent reading
        :return: Magnetic field strength of X,Y,Z axes
        :rtype: (int, int, int)
        """
        results = self._read_multiple(_MX, 9)
        results = [int.from_bytes(results[x : x + 3], "big") for x in range(0, 9, 3)]
        return tuple(x - 0x01000000 if x > 0x00800000 else x for x in results)

    def get_single_reading(self) -> Tuple[int, int, int]:
        """
        Get a single reading from the RM3100

        :return: Magnetic field strength of X,Y,Z axes
        :rtype: (int, int, int)
        """
        # start read
        self._write_reg(_POLL, bytearray([0x70]))
        time.sleep(_CYCLE_DURATION * self.cycle_count)
        self.wait_for_fresh_reading()
        return self.get_last_reading()

    # async def aio_get_single_reading(self) -> Tuple[int]:
    #     self._write_reg(_POLL, bytearray([0x70]))
    #     time.sleep(_CYCLE_DURATION * self.cycle_count)
    #     return self._get_reading()

    def start_continuous_reading(self, frequency: float = 300):
        """
        Start continuously reading at the given frequency.
        :param frequency: Valid frequencies are 600Hz, 300Hz, 150Hz, 75Hz, 37Hz, 18Hz,
        9Hz, 4.5Hz, 2.3Hz, 1.2Hz, 0.6Hz, 0.3Hz, 0.015Hz. 0.0075Hz.
        The nearest valid frequency is selected. Note that the cycle count may override this value.
        """
        # write frequency
        exponent = round(math.log2(600 / frequency))
        exponent = min(13, exponent)
        value = 0x92 + int(exponent)
        self._write_reg(_TMRC, bytearray([value]))
        # start continuous reading, using all three axes
        self._write_reg(_CMM, bytearray([0x71]))
        self.continuous = True

    def get_next_reading(self) -> Tuple[int, int, int]:
        """
        Get the next reading when in continuous mode. Raises ValueError if not in continuous mode

        :return: Magnetic field strength of X,Y,Z axes
        :rtype: (int, int, int)
        """
        if not self.continuous:
            raise ValueError("RM3100 not in continuous mode")
        self.wait_for_fresh_reading()
        return self.get_last_reading()

    def stop(self):
        """
        Stop continuous mode
        """
        self._write_reg(_CMM, bytearray([0x70]))
        self.continuous = False

    def _write_reg(self, addr: int, data: bytes):
        raise NotImplementedError

    def _read_multiple(self, addr: int, size: int):
        raise NotImplementedError

    def _read_reg(self, addr: int) -> int:
        result = self._read_multiple(addr, 1)
        return result[0]


class RM3100_I2C(_RM3100):
    """
    Driver for RM3100 magnetometer using I2C interface

    :param ~busio.I2C bus: The I2C bus the RM3100 is connected to
    :param int address: The I2C device address. Defaults to :const:`0x20`
    :param int cycle_count: Number of oscillations used to measure magnetic field.
        Higher numbers give more accurate results, but takes longer to measure.
        Each cycle takes approximately 36 microseconds. Default is 200.
    :param ~digitalio.DigitalInOut int_pin: Pin connected to DRDY of RM3100. DRDY signals when
        the RM3100 has completed a measurement. If `None`, the STATUS register will be polled
        to see when measurement is complete. Default is `None`
    """

    def __init__(
        self,
        bus: I2C,
        i2c_address: int = 0x20,
        cycle_count: int = 200,
        int_pin: Optional[Pin] = None,
    ):
        self.device: I2CDevice = I2CDevice(bus, i2c_address)
        super().__init__(cycle_count, int_pin)

    def _write_reg(self, addr: int, data: bytes):
        data = bytes([addr]) + data
        with self.device:
            self.device.write(data)

    def _read_multiple(self, addr: int, size: int) -> bytearray:
        result = bytearray(size)
        with self.device:
            self.device.write_then_readinto(bytes([addr]), result)
        return result


class RM3100_SPI(_RM3100):
    """
    Driver for RM3100 magnetometer using I2C interface

    :param ~busio.SPI bus: The SPI bus the RM3100 is connected to
    :param ~digitalio.DigitalInOut chip_select: Chip Select
    :param int cycle_count: Number of oscillations used to measure magnetic field.
        Higher numbers give more accurate results, but takes longer to measure.
        Each cycle takes approximately 36 microseconds. Default is 200.
    :param ~digitalio.DigitalInOut int_pin: Pin connected to DRDY of RM3100.
        DRDY signals when the RM3100 has completed a measurement. If `None`, the STATUS
        register will be polled to see when measurement is complete. Default is `None`
    """

    def __init__(
        self,
        bus: SPI,
        chip_select: digitalio.DigitalInOut,
        cycle_count: int = 200,
        int_pin: Optional[digitalio.DigitalInOut] = None,
    ):
        self.device = SPIDevice(bus, chip_select)
        super().__init__(cycle_count, int_pin)

    def _write_reg(self, addr: int, data: bytes):
        data = bytes([addr]) + data
        with self.device as spi:
            spi.write(data)

    def _read_multiple(self, addr: int, size: int) -> bytearray:
        result = bytearray(size + 1)
        output = bytearray(size + 1)
        output[0] = addr | 0x80  # set upper bit to signal a read
        with self.device as spi:
            spi.write_readinto(output, result)
        return result[1:]  # ignore first byte read as it is always blank
