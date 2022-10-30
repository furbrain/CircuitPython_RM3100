# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2022 Phil Underwood for Underwood Underground
#
# SPDX-License-Identifier: Unlicense
import time
import board
import rm3100

i2c = board.I2C()
rm = rm3100.RM3100_I2C(i2c, i2c_address=0x23)

while True:
    rm.start_single_reading()
    time.sleep(rm.get_measurement_time())
    print(rm.get_next_reading())
