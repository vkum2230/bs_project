import serial
import time

ser = serial.Serial('/dev/ttyAMA0', 115200, timeout=1)

send_data = "Hello Raspberry Pi 5!\n"
        
ser.write(send_data.encode('utf-8'))

print("send success")


try:
    while True:
        if ser.in_waiting:
            
            data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            print(data, end='', flush=True)
except KeyboardInterrupt:
    ser.close()