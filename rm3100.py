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
_LN2 = 0.693147  # log(2)
_UT_PER_CYCLE = 2.5000  # µT per lsb per cycle


class _RM3100:
    """
    Communicate with RM3100 magnetometers, using SPI or I2C interfaces
    This is an abstract parent class, please use RM3100_I2C or RM3100_SPI
    """

    def __init__(self, cycle_count: int = 200, drdy_pin: Optional[Pin] = None):
        self.cycle_count = cycle_count
        self.drdy_pin = drdy_pin
        # set cycle count
        values = struct.pack(
            ">HHH", self.cycle_count, self.cycle_count, self.cycle_count
        )
        self._write_reg(_CCX, values)
        self.continuous = False

    @property
    def measurement_complete(self) -> bool:
        """
        Whether the most recent reading has finished.
        """
        if self.drdy_pin is not None:
            return self.drdy_pin.value
        # no DRDY pin, so poll the status register
        status = self._read_reg(_STATUS)
        return status & 0x80 != 0

    def get_last_reading(self) -> Tuple[int, int, int]:
        """
        Get the most recent reading

        :return: Raw magnetic field strength of X,Y,Z axes
        :rtype: (int, int, int)
        """
        results = self._read_multiple(_MX, 9)
        results = [int.from_bytes(results[x : x + 3], "big") for x in range(0, 9, 3)]
        return tuple(x - 0x01000000 if x > 0x00800000 else x for x in results)

    def start_single_reading(self):
        """
        Start a single measurement cycle
        """
        # start read
        self._write_reg(_POLL, bytearray([0x70]))

    @property
    def measurement_time(self) -> float:
        """
        Time needed to complete a measurement, in seconds
        """
        return _CYCLE_DURATION * self.cycle_count

    def start_continuous_reading(self, frequency: float = 300):
        """
        Start continuously reading at the given frequency. It is recommended that you use the DRDY
        line to detect measurement occurrences. Polling for new readings frequently can cause
        electronic noise that adversely affects accuracy.

        :param frequency: Valid frequencies are 600Hz, 300Hz, 150Hz, 75Hz, 37Hz, 18Hz,
            9Hz, 4.5Hz, 2.3Hz, 1.2Hz, 0.6Hz, 0.3Hz, 0.015Hz. 0.0075Hz.
            The nearest valid frequency is selected. Note that the cycle count may override
            this value, if taking a reading would be longer than the sample interval.

        """
        # write frequency
        exponent = round(math.log(600 / frequency) / _LN2)
        exponent = min(13, exponent)
        print(exponent)
        value = 0x92 + int(exponent)
        self._write_reg(_TMRC, bytearray([value]))
        # start continuous reading, using all three axes
        self._write_reg(_CMM, bytearray([0x79]))
        self.continuous = True

    def get_next_reading(self, poll_interval=0.01) -> Tuple[int, int, int]:
        """
        Get the next reading, can hang forever if not in continuous mode and
        start_single_reading has not been called. Can cause increased signal noise if the
        DRDY pin is not used.

        :param float poll_interval: How frequently to check if next reading is ready,
            default is 0.01s

        :return: Raw magnetic field strength of X,Y,Z axes
        :rtype: (int, int, int)
        """
        while not self.measurement_complete:
            time.sleep(poll_interval)
        return self.get_last_reading()

    def stop(self):
        """
        Stop continuous mode
        """
        self._write_reg(_CMM, bytearray([0x70]))
        self.continuous = False

    def convert_to_microteslas(
        self, value: Tuple[int, int, int]
    ) -> Tuple[float, float, float]:
        """
        Convert raw reading to reading in µT. This is dependent on the cycle
        count selected.
        :param (int, int, int) value: raw reading
        :return: Reading in µT
        :rtype: (float,float,float)
        """
        factor = _UT_PER_CYCLE / self.cycle_count
        return tuple(x * factor for x in value)

    @property
    def magnetic(self) -> Tuple[float, float, float]:
        """
        Magnetic field strength in x,y,z axes, in µT, uses most recent reading
        """
        if not self.continuous:
            self.start_single_reading()
            time.sleep(self.measurement_time)
        values = self.get_next_reading()
        return self.convert_to_microteslas(values)

    def _write_reg(self, addr: int, data: bytes):
        raise NotImplementedError

    def _read_multiple(self, addr: int, size: int):
        raise NotImplementedError

    def _read_reg(self, addr: int) -> int:
        result = self._read_multiple(addr, 1)
        return result[0]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.continuous:
            self.stop()


class RM3100_I2C(_RM3100):
    """
    Driver for RM3100 magnetometer using I2C interface

    :param ~busio.I2C bus: The I2C bus the RM3100 is connected to
    :param int address: The I2C device address. Defaults to :const:`0x20`
    :param int cycle_count: Number of oscillations used to measure magnetic field.
        Higher numbers give more accurate results, but takes longer to measure.
        Each cycle takes approximately 36 microseconds. Default is 200.
    :param ~digitalio.DigitalInOut drdy_pin: Pin connected to DRDY of RM3100. DRDY signals when
        the RM3100 has completed a measurement. If `None`, the STATUS register will be polled
        to see when measurement is complete. Default is `None`
    """

    def __init__(
        self,
        bus: I2C,
        i2c_address: int = 0x20,
        cycle_count: int = 200,
        drdy_pin: Optional[Pin] = None,
    ):
        self.device: I2CDevice = I2CDevice(bus, i2c_address)
        super().__init__(cycle_count, drdy_pin)

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
        Each cycle takes approximately 36 microseconds for 3 axes. Default is 200.
    :param ~digitalio.DigitalInOut drdy_pin: Pin connected to DRDY of RM3100.
        DRDY signals when the RM3100 has completed a measurement. If `None`, the STATUS
        register will be polled to see when measurement is complete. Default is `None`
    """

    def __init__(
        self,
        bus: SPI,
        chip_select: digitalio.DigitalInOut,
        cycle_count: int = 200,
        drdy_pin: Optional[digitalio.DigitalInOut] = None,
    ):
        self.device = SPIDevice(bus, chip_select)
        super().__init__(cycle_count, drdy_pin)

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
