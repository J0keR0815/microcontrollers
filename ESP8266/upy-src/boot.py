"""
This file is executed on every boot
(including wake-boot from deepsleep)
"""

import esp
import gc
import machine  # noqa: F401
import network
import sys  # noqa: F401
import uos  # noqa: F401
# import webrepl


def singleton(cls):
    """
    This function is used as a decorator to use the singleton pattern.
    """

    instance = None

    def get_instance(*args, **kwargs):
        nonlocal instance
        if instance is None:
            instance = cls(*args, **kwargs)
        return instance

    return get_instance


def functor(cls):
    """
    This function is used as a decorator to use a functor pattern.
    """

    instance = None

    def get_instance(*args, **kwargs):
        nonlocal instance
        if instance is None:
            instance = cls(*args, **kwargs)
            return instance
        return instance(*args, **kwargs)

    return get_instance


# esp.osdebug(None)
# uos.dupterm(None, 1)  # disable REPL on UART(0)
# webrepl.start()
gc.collect()
# Turn of Wifi
network.WLAN(network.STA_IF).active(False)
esp.sleep_type(esp.SLEEP_MODEM)
network.WLAN(network.AP_IF).active(False)
