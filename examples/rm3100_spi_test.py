# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2022 Phil Underwood for Underwood Underground
#
# SPDX-License-Identifier: Unlicense

import time
import board
import digitalio
import rm3100

spi = board.SPI()
int_pin = digitalio.DigitalInOut(board.D3)
int_pin.direction = digitalio.Direction.INPUT

cs_pin = digitalio.DigitalInOut(board.D4)
cs_pin.direction = digitalio.Direction.OUTPUT
cs_pin.value = True
rm = rm3100.RM3100_SPI(spi, chip_select=cs_pin, drdy_pin=int_pin)


rm.start_continuous_reading(1.2)  # start continuous reading at 1.2Hz
for i in range(20):
    print(rm.get_next_reading())
    time.sleep(0.6)
rm.stop()
