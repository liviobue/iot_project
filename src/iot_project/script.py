import os
import datetime
import enum
import time
import dataclasses
import struct
import math
import binascii
import typing

import dotenv
import smbus
import pymongo
import trio
import numpy as np
import RPi.GPIO as GPIO
import httpx


from iot_project.multigas_class import MultiGasSensor
from iot_project.db_connect import *


%autoawait trio


i2cbus          = 1
NH3_ADDRESS     = 0x75
CO_ADDRESS      = 0x76
O2_ADDRESS      = 0x77

buttonpin       = 18
buzzerpin       = 17
nh3_led_red     = 23
co_led_red      = 24
o2_led_red      = 25
led_green       = 12

nh3_alert       = False
co_alert        = False
o2_alert        = False

NH3             = MultiGasSensor(i2cbus, NH3_ADDRESS, SensorType.NH3)
CO              = MultiGasSensor(i2cbus, CO_ADDRESS, SensorType.CO)
O2              = MultiGasSensor(i2cbus, O2_ADDRESS, SensorType.O2)



def setup():
    GPIO.setmode(GPIO.BCM) # use LOGICAL GPIO Numbering

    # Green LED
    GPIO.setup(led_green, GPIO.OUT)
    GPIO.output(led_green, GPIO.HIGH) # make green ledPin output HIGH level

    # NH3-LED
    GPIO.setup(nh3_led_red, GPIO.OUT) # set the red ledPin to OUTPUT mode
    GPIO.output(nh3_led_red, GPIO.LOW) # make red ledPin output LOW level

    # CO-LED
    GPIO.setup(co_led_red, GPIO.OUT) # set the red ledPin to OUTPUT mode
    GPIO.output(co_led_red, GPIO.LOW) # make red ledPin output LOW level

    # O2-LED
    GPIO.setup(o2_led_red, GPIO.OUT) # set the red ledPin to OUTPUT mode
    GPIO.output(o2_led_red, GPIO.LOW) # make red ledPin output LOW level

    # Buzzer-Pin
    GPIO.setup(buzzerpin, GPIO.OUT) # set buzzerPin to OUTPUT modea

    # Button
    GPIO.setup(buttonpin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # set buttonPin to PULL UP INPUT mode



async def wait_for_alert_end(max_wait_time, previous_button_state) -> tuple[typing.Literal["timeout", "button pressed", "no more alert"], bool]:
    
    with trio.move_on_after(max_wait_time): # Runs until max_wait_time is over
        while True:
            current_button_state = GPIO.input(buttonpin)==GPIO.LOW
            if not previous_button_state and current_button_state:
                return "button pressed", previous_button_state

            if not (nh3_alert or co_alert or o2_alert):
                return "no more alert", previous_button_state

            previous_button_state = current_button_state
            await trio.sleep(0.05)
    
    return "timeout", previous_button_state



async def alert():
    """
    Check if an alert is present or not
    If alert is not present: normal mode and 10ms sleep
    If alert is present: LED & Buzzer on and blinking
    """   
    while True:  

        """NORMAL-MODE"""
        if not (nh3_alert or co_alert or o2_alert):
            normal_mode()
            await trio.sleep(0.1)
            continue

        
        """ALERT-MODE"""
        GPIO.output(led_green, GPIO.LOW)
        button_state = True
        
        while True:

            # Blink-On-Phase
            GPIO.output(nh3_led_red, GPIO.HIGH if nh3_alert else GPIO.LOW)
            GPIO.output(co_led_red, GPIO.HIGH if co_alert else GPIO.LOW)
            GPIO.output(o2_led_red, GPIO.HIGH if o2_alert else GPIO.LOW)
            GPIO.output(buzzerpin, GPIO.HIGH)
            
            result, button_state = await wait_for_alert_end(0.4, button_state)           
            if result != "timeout":
                break # -> to ACKNOWLEDGE-MODE or to Normal-State
            
            # Blink-Off-Phase
            GPIO.output(nh3_led_red, GPIO.LOW)
            GPIO.output(co_led_red, GPIO.LOW)
            GPIO.output(o2_led_red, GPIO.LOW)
            GPIO.output(buzzerpin, GPIO.LOW)
            
            result, button_state = await wait_for_alert_end(0.4, button_state)
            if result != "timeout":
                break # -> to ACKNOWLEDGE-MODE or to Normal-State

        
        if result == "button pressed":
            """
            ACKNOWLEDGE-MODE:
            - LEDs on, Buzzer off
            - If Button is pressed again: ACKNOWLEDGE-MODE is aborted
            -> alert-mode is reactivated if there is still an alert, otherwise it goes back to normal
            """
            previous_button_state = True # Button was pressed before
            GPIO.output(buzzerpin, GPIO.LOW)

            while nh3_alert or co_alert or o2_alert:
                current_button_state = GPIO.input(buttonpin)==GPIO.LOW

                if not previous_button_state and current_button_state: # Checks if there was a change from not-pressed to pressed
                    break
                
                GPIO.output(nh3_led_red, GPIO.HIGH if nh3_alert else GPIO.LOW)
                GPIO.output(co_led_red, GPIO.HIGH if co_alert else GPIO.LOW)
                GPIO.output(o2_led_red, GPIO.HIGH if o2_alert else GPIO.LOW)

                previous_button_state = current_button_state
                await trio.sleep(0.1)



def normal_mode():
    """
    Mode without alert
    """    
    GPIO.output(led_green, GPIO.HIGH)
    GPIO.output(nh3_led_red, GPIO.LOW)
    GPIO.output(co_led_red, GPIO.LOW)
    GPIO.output(o2_led_red, GPIO.LOW)
    GPIO.output(buzzerpin, GPIO.LOW)



def aggregate_data(alldata):
    data = np.array([data for time, data in alldata])

    min = data.min()
    max = data.max()
    avg = data.mean()

    aggregation = dict(
        min=min,
        max=max,
        avg=avg,
    )
    
    return aggregation



async def measurement(*,measurement_interval=0.1, aggregation_interval=10):
    
    global nh3_alert
    global co_alert
    global o2_alert

    nh3_alert_level = 50 # Normally above 50 PPM for a 8-Hour-Shift
    co_alert_level = 100 # Normally above 100PPM
    o2_alert_level = 20 # Normally below 17%

    
    next_measurement = trio.current_time()+measurement_interval
    next_aggregation = trio.current_time()+aggregation_interval

    i=0
    while True:
        alldata_nh3 = [] # um alle Daten zu speichern (!Überlegen wegen Memory)   
        alldata_co = []
        alldata_o2 = []
        
        while trio.current_time()<next_aggregation:      
            try:
                time = datetime.datetime.now().astimezone(None).astimezone(datetime.timezone.utc)

                ammonia = NH3.read_all().gas_concentration
                carbon_monoxide = CO.read_all().gas_concentration
                oxygen = O2.read_all().gas_concentration
                
            except Exception as ex:
                #print(f'{ex!r} - retry')
                await trio.sleep(0.05)
                continue
    
            alldata_nh3.append((time, ammonia))
            alldata_co.append((time, carbon_monoxide))
            alldata_o2.append((time, oxygen))
            
            # Check if alerts are True
            nh3_alert = ammonia>nh3_alert_level
            co_alert = carbon_monoxide>co_alert_level
            o2_alert = oxygen<o2_alert_level

            await trio.sleep_until(next_measurement)
            next_measurement += measurement_interval

        # Aggregate Data
        next_aggregation += aggregation_interval
        
        aggregation_nh3 = aggregate_data(alldata_nh3)
        aggregation_co = aggregate_data(alldata_co)
        aggregation_o2 = aggregate_data(alldata_o2)

        aggregation = dict(
            time=time,
            NH3=aggregation_nh3,
            CO=aggregation_co,
            O2=aggregation_o2,
        )

        insert_data_to_db(aggregation)
        
        print(aggregation)


def main():
    setup()
    
    try: 
        async with trio.open_nursery() as nursery:
            nursery.start_soon(alert)
            nursery.start_soon(measurement)
    finally:
        GPIO.cleanup()



