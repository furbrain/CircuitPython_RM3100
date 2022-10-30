Introduction
============


.. image:: https://readthedocs.org/projects/circuitpython-rm3100/badge/?version=latest
    :target: https://circuitpython-rm3100.readthedocs.io/
    :alt: Documentation Status



.. image:: https://img.shields.io/discord/327254708534116352.svg
    :target: https://adafru.it/discord
    :alt: Discord


.. image:: https://github.com/furbrain/CircuitPython_RM3100/workflows/Build%20CI/badge.svg
    :target: https://github.com/furbrain/CircuitPython_RM3100/actions
    :alt: Build Status


.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
    :alt: Code Style: Black

Driver for the RM3100 magnetometer by PNI Sensor Corporation


Dependencies
=============
This driver depends on:

* `Adafruit CircuitPython <https://github.com/adafruit/circuitpython>`_
* `Bus Device <https://github.com/adafruit/Adafruit_CircuitPython_BusDevice>`_

Please ensure all dependencies are available on the CircuitPython filesystem.
This is easily achieved by downloading
`the Adafruit library and driver bundle <https://circuitpython.org/libraries>`_
or individual libraries can be installed using
`circup <https://github.com/adafruit/circup>`_.

Installing from PyPI
=====================

On supported GNU/Linux systems like the Raspberry Pi, you can install the driver locally `from
PyPI <https://pypi.org/project/circuitpython-rm3100/>`_.
To install for current user:

.. code-block:: shell

    pip3 install circuitpython-rm3100

To install system-wide (this may be required in some cases):

.. code-block:: shell

    sudo pip3 install circuitpython-rm3100

To install in a virtual environment in your current project:

.. code-block:: shell

    mkdir project-name && cd project-name
    python3 -m venv .venv
    source .env/bin/activate
    pip3 install circuitpython-rm3100

Installing to a Connected CircuitPython Device with Circup
==========================================================

Make sure that you have ``circup`` installed in your Python environment.
Install it with the following command if necessary:

.. code-block:: shell

    pip3 install circup

With ``circup`` installed and your CircuitPython device connected use the
following command to install:

.. code-block:: shell

    circup install rm3100

Or the following command to update an existing version:

.. code-block:: shell

    circup update

Usage Examples
==============

.. code-block:: python

    # Example using I2C and single measurement readings, no DRDY pin

    import time
    import board
    import rm3100

    i2c = board.I2C()
    rm = rm3100.RM3100_I2C(i2c, i2c_address=0x23)

    while True:
        rm.start_single_reading()
        time.sleep(rm.get_measurement_time())
        print(rm.get_next_reading())

.. code-block:: python

    # Example using SPI and a DRDY pin, using continuous readings

    import board
    import digitalio
    import rm3100

    spi = board.SPI()
    drdy_pin = digitalio.DigitalInOut(board.D3)
    drdy_pin.direction = digitalio.Direction.INPUT

    cs_pin = digitalio.DigitalInOut(board.D4)
    cs_pin.direction = digitalio.Direction.OUTPUT
    cs_pin.value = True
    rm = rm3100.RM3100_SPI(spi, chip_select=cs_pin, drdy_pin=drdy_pin)


    rm.start_continuous_reading(1.2)  # start continuous reading at 1.2Hz
    for i in range(20):
        print(rm.get_next_reading())
    rm.stop()


Documentation
=============
API documentation for this library can be found on `Read the Docs <https://circuitpython-rm3100.readthedocs.io/>`_.

For information on building library documentation, please check out
`this guide <https://learn.adafruit.com/creating-and-sharing-a-circuitpython-library/sharing-our-docs-on-readthedocs#sphinx-5-1>`_.

Contributing
============

Contributions are welcome! Please read our `Code of Conduct
<https://github.com/furbrain/CircuitPython_RM3100/blob/HEAD/CODE_OF_CONDUCT.md>`_
before contributing to help this project stay welcoming.
