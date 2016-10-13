import serial
import mongomodels as models


def setup_serial():
    serial_interface = serial.Serial(models.compost_Settings.objects.first().usb_port, 115200)
    return serial_interface
