import serial
import mongomodels as models

# ser = serial.Serial(models.compost_Settings.objects.first().usb_port, 115200)  # setup serial communication port
print(type(models.compost_Settings.objects.first().usb_port))
