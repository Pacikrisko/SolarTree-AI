import time
import board
import busio
from analogio import AnalogIn
import neopixel
import digitalio

from solar_upload import SolarLink
from rgb1602 import Screen
from adafruit_bme280 import basic as adafruit_bme280


# -------------------------
# PIN SETUP
# waveshare lcd1602 and bme280-"gp0=sda, gp1=scl"w
# joystick-"Y axis"=gp28(adc2)
# joystick-"B"= gp15
# mq-8-"Dout"= gp26(adc0)
# -------------------------

i2c = busio.I2C(board.GP1, board.GP0)

# Analog inputs
mq8 = AnalogIn(board.GP26)
joystick_y = AnalogIn(board.GP28)

# Button on GP15 (active-low)
button = digitalio.DigitalInOut(board.GP15)
button.switch_to_input(pull=digitalio.Pull.UP)

# LCD1602
lcd = Screen(i2c)
lcd.set_rgb(0,90,6)

# BME280
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
bme280.sea_level_pressure = 1013.25


# NeoPixel stick
NEOPIXEL_PIN = board.GP4
NUM_PIXELS = 8
pixels = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS,
                           brightness=0.4, auto_write=False)


# -------------------------
# STATE VARIABLES
# -------------------------

link = SolarLink()
SCREEN_COUNT = 4
current_screen = 0

# Manual scrolling mode by default
auto_mode = False

# For debouncing the button
last_button_state = True
last_button_time = 0
BUTTON_DEBOUNCE = 0.2  # seconds

# Timer for auto-scrolling
last_auto_switch = 0
AUTO_INTERVAL = 5.0

# Joystick deadzone
JOYSTICK_CENTER = 32768
JOYSTICK_DEADZONE = 5000
last_direction = 0


# -------------------------
# FUNCTIONS
# -------------------------

def read_joystick_direction():
    value = joystick_y.value
    if abs(value - JOYSTICK_CENTER) < JOYSTICK_DEADZONE:
        return 0
    elif value > JOYSTICK_CENTER + JOYSTICK_DEADZONE:
        return 1
    else:
        return -1


def show_mq8_screen():
    raw = mq8.value
    voltage = (raw * 3.3) / 65535.0
    line1 = "MQ-8 gas sensor"
    line2 = "ADC:{:5d} V:{:1.2f}".format(raw, voltage)
    lcd.update(line1, line2)


def show_bme280_screen_second():
    pressure = bme280.pressure
    altitude = bme280.altitude
    line1 = "Pressure:{:4.0f}hPa".format(pressure)
    line2 = "Altitude:{:5.0f}m".format(altitude)
    lcd.update(line1, line2)


def show_bme280_screen():
    temperature = bme280.temperature
    humidity = bme280.relative_humidity
    line1 = "Temp:{:4.1f}C".format(temperature)
    line2 = "Humidity:{:2.0f}%".format(humidity)
    lcd.update(line1, line2)


def update_h2_led_bar():
    raw = mq8.value
    fraction = raw / 65535.0
    num_lit = int(fraction * NUM_PIXELS + 0.5)

    for i in range(NUM_PIXELS):
        pixels[i] = (0, 0, 255) if i < num_lit else (0, 0, 0)

    pixels.show()


# -------------------------
# MAIN LOOP
# -------------------------

while True:
    now = time.monotonic()

    update_h2_led_bar()
    
    current_button_state = button.value 

    if current_button_state != last_button_state:
        if now - last_button_time > BUTTON_DEBOUNCE:
            last_button_time = now
            last_button_state = current_button_state

            if current_button_state is False:  
                auto_mode = not auto_mode  
                last_auto_switch = now     

    if not auto_mode:
        # MANUAL MODE
        direction = read_joystick_direction()
        if direction != 0 and last_direction == 0:
            if direction == 1:
                current_screen = (current_screen + 1) % SCREEN_COUNT
            elif direction == -1:
                current_screen = (current_screen - 1) % SCREEN_COUNT
        last_direction = direction

    else:
        # AUTO MODE (switch every 5 seconds)
        if now - last_auto_switch >= AUTO_INTERVAL:
            current_screen = (current_screen + 1) % SCREEN_COUNT
            last_auto_switch = now


    if current_screen == 0:
        show_mq8_screen()
    elif current_screen == 1:
        show_bme280_screen_second()
    elif current_screen == 2:
        show_bme280_screen()

    else:
        lcd.update(*link.display())

    link.tick(bme280, mq8)
    time.sleep(0.5)
