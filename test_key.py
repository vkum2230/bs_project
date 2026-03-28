from gpiozero import Button
from time import sleep
button = Button(2)
while True:
    if button.is_pressed:
        print("Button is PRESSED")
    else:
        print("Button is NOT pressed")
    sleep(0.5)