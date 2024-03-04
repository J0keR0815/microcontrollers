"""
This module provides a controller-interface for the microcontroller
"""

# Imports from libraries

import network

# Local imports

from boot import singleton


@singleton
class Controller:
    __instance = None

    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)

    def start_wifi(self):
        self.wlan.active(True)

    def stop_wifi(self):
        self.wlan.active(False)

    def connect_wifi(self, essid, pw):
        self.wlan.connect(essid, pw)

    def disconnect_wifi(self):
        self.wlan.disconnect()


if __name__ == "__main__":
    contr = Controller()
