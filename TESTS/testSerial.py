import serial
import json

ser = serial.Serial('COM32', 115200)  # setup serial communication port
ser.write('/id\r'.encode())
# try:
a = ser.readline()
print(a)
# except serial.SerialTimeoutException:
print('skata')
