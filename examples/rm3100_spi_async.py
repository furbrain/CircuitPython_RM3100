# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2022 Phil Underwood for Underwood Underground
#
# SPDX-License-Identifier: Unlicense
"""
This script demonstrates how to use asyncio to trigger a reading and then
wait a correct amount of time before reading from the device and converting to µT.
You will need to do `circup install asyncio` to use the asyncio functions
"""
import asyncio

import board
import digitalio
import rm3100

spi = board.SPI()

cs_pin = digitalio.DigitalInOut(board.D4)
cs_pin.direction = digitalio.Direction.OUTPUT
cs_pin.value = True


async def main():
    with rm3100.RM3100_SPI(spi, chip_select=cs_pin) as rm:
        for _ in range(20):
            rm.start_single_reading()
            await asyncio.sleep(rm.measurement_time)
            result = rm.convert_to_microteslas(rm.get_next_reading())
            print(result)


asyncio.run(main())
