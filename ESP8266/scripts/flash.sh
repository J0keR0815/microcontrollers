#!/bin/bash
# 
# Dieses Script flasht einen ESP8266 mit der als Parameter übergebenen Firmware
# 
# Usage:	flash.sh <device> <firmware-file>
 
# Parameter überprüfen
if [ $# -ne 2 ]
then
    echo "Usage: $(basename $0) <device> <firmware>" >&2
    exit 1
fi
 
# Verbindung testen (MAC-Adresse auslesen)
esptool.py -p $1 read_mac
if [ $? -eq 0 ]
then
	##### Flash 2-Zeiler ##################
	esptool.py -p $1 -b 460800 erase_flash 
	esptool.py -p $1 -b 460800 write_flash --flash_size=detect -fm dio 0 $2
	##### Flash - Ende
 
	RETVAL=$?
	if [ $RETVAL -eq 0 ]
	then
	    echo "Firmware $2 auf Gerät $1 geschrieben"
	else
	    echo "Error in $(basename $0): Firmware konnte nicht geschrieben werden" >&2
	fi
	exit $RETVAL
elif [ $? -eq 127 ]
then
	echo "Error in $(basename $0): esptool.py nicht gefunden" >&2
else 
	echo "Error in $(basename $0): Kommunikationsfehler" >&2
fi
