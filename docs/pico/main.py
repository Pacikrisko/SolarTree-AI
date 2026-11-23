"""SolarTree prototype telemetry for MicroPython on Raspberry Pi Pico 2 W.

Sends ONLY values actually read from BME280 (when driver is installed) and MQ-8 ADC.
No fake watts, oxygen volume, tank level, or hydrogen concentration.
Not a hydrogen safety system; the real hardware needs independent protection.
"""
import time
import network
import machine
import ujson
try:
    import urequests
except ImportError:
    import requests as urequests  # for recent MicroPython builds
from machine import Pin, I2C, ADC
from pico_config import WIFI_SSID, WIFI_PASSWORD, SERVER_URL, DEVICE_CODE, DEVICE_KEY, INTERVAL_SECONDS

mq8 = ADC(Pin(26))
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100000)
try:
    import bme280
    bme = bme280.BME280(i2c=i2c)
except Exception as e:
    bme = None
    print('BME280 is not available:', e)

wifi = network.WLAN(network.STA_IF)
wifi.active(True)

def ensure_wifi():
    if wifi.isconnected():
        return True
    wifi.connect(WIFI_SSID, WIFI_PASSWORD)
    for _ in range(25):
        if wifi.isconnected():
            print('Wi-Fi connected:', wifi.ifconfig()[0]);return True
        time.sleep(1)
    return False

def to_float(value):
    if isinstance(value, (int, float)):
        return float(value)
    value = str(value).strip().lower().replace('°c','').replace('c','').replace('%','')
    return float(value.strip())

def read_sensors():
    measurements = {'mq8_adc_raw': mq8.read_u16()}
    if bme is not None:
        try:
            measurements['temperature_c'] = round(to_float(bme.temperature), 2)
            measurements['humidity_pct'] = round(to_float(bme.humidity), 2)
        except Exception as exc:
            print('BME280 measurement error:', exc)
    return measurements

def send(data):
    path = SERVER_URL.rstrip('/') + '/api/device/' + DEVICE_CODE + '/sensors'
    response = None
    try:
        response = urequests.post(path, data=ujson.dumps(data),
            headers={'Content-Type':'application/json', 'X-Device-Key':DEVICE_KEY}, timeout=8)
        print('Upload:', response.status_code, response.text[:180])
        return response.status_code == 200
    except Exception as exc:
        print('Upload error:', exc)
        return False
    finally:
        if response is not None:
            response.close()

while True:
    if ensure_wifi():
        data = read_sensors()
        print('Measured:', data)
        send(data)
    else:
        print('Wi-Fi offline: verify SSID/password and network')
    time.sleep(max(5, INTERVAL_SECONDS))
