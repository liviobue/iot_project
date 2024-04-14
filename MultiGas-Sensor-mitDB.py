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
import bokeh.io
import bokeh.plotting
import bokeh.models
import bokeh as bk
import numpy as np
import RPi.GPIO as GPIO
import httpx

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



def connect_to_db():
    """Open the connection to the DB and return the collection
    Create collection with unique index, if there is not yet one"""
    # Load environment variables from .env file
    
    dotenv.load_dotenv()
    
    # Get MongoDB-URI
    mongodb_uri = os.getenv("MONGODB_URI")
    DBclient = pymongo.MongoClient(mongodb_uri)
    db = DBclient["IoT-Project"]

    return db["Raw-Data"]


def represent_for_mongodb(obj):
    match obj:
        case dict():
            return {represent_for_mongodb(k):represent_for_mongodb(v) for k,v in obj.items()}
        case tuple() | list():
            return type(obj)(represent_for_mongodb(v) for v in obj)
        case np.generic():
            return obj.item()
        case _:
            return obj


def insert_data_to_db(data):
    collection = connect_to_db()
    collection.insert_one(
        represent_for_mongodb(data)
    )


class CmdCode(enum.Enum):
    read_concentration = 0x86
    read_temp = 0x87
    read_all = 0x88


class SensorType(enum.Enum):
    O2         =  0x05
    CO         =  0x04
    H2S        =  0x03
    NO2        =  0x2C
    O3         =  0x2A
    CL2        =  0x31
    NH3        =  0x02
    H2         =  0x06
    HCL        =  0X2E
    SO2        =  0X2B
    HF         =  0x33
    PH3        =  0x45


@dataclasses.dataclass
class SensorData:
    gas_concentration: float  # ppm
    sensor_type: SensorType
    temperature: float        # degree Celsius


class MultiGasSensor:
    """
    Class for all Gas-Sensors
    Adapted from https://github.com/DFRobot/DFRobot_MultiGasSensor
    """
    
    def __init__(self, bus_number: int, i2c_address: int, expected_sensor_type: SensorType | None = None):
        self.i2c_bus = smbus.SMBus(bus_number)
        self.i2c_address = i2c_address
        self.expected_sensor_type = expected_sensor_type

    
    @classmethod
    def calc_check_sum(cls, data:bytes)->int:
        return (~sum(data)+1) & 0xff

    
    def command(self, code: CmdCode, *args:bytes) -> bytes:
        data = bytes([0xFF, 0x01, code.value]) + b"".join(args)
        data += b"\x00"*(8-len(data))
        data += bytes([self.calc_check_sum(data[1:-1])])
        self.i2c_bus.write_i2c_block_data(self.i2c_address, 0, list(data))
        time.sleep(0.1)                                                         # TO-DO: async-sleept machen
        
        result = self.i2c_bus.read_i2c_block_data(self.i2c_address, 0, 9)
        result = bytes(result)
        result_str = binascii.hexlify(result," ",1)
        
        assert result[0] == 0xFF, result_str
        assert result[1] == code.value, result_str
        assert result[8] == self.calc_check_sum(result[1:-2]), f"CRC failure: received 0x{result[8]:02x}, calculated 0x{self.calc_check_sum(result[1:-1]):02x}, ({result_str})"

        return result[2:-1]

    
    def read_all(self) -> SensorData:
        result = self.command(CmdCode.read_all)

        # '>': big-endian encoded struct (MSB first: most significant byte first);
        # 'H': 2 Bytes unsigned integer ("half long integer")
        # 'B': 1 Byte unsigned integer  ("byte")
        gas_concentration_raw, sensor_type, decimal_places, temperature_raw = struct.unpack(">HBBH", result)
        gas_concentration = gas_concentration_raw * 10**-decimal_places
        sensor_type = SensorType(sensor_type)
   
        Vpd3 = 3*temperature_raw/1024 # Spannung in Volt
        Rth = Vpd3*10000/(3-Vpd3) # Spannung mit Spannnungsteiler vonem 10k-Widerstand
        temperature = 1/(1/(273.15+25)+1/3380.13*(math.log(Rth/10000)))-273.15 # Transfer-Kurve von temperaturfühler mit 10kOhm bei 25°C und alpha-Wert von 3380.13

        if self.expected_sensor_type is not None:
            assert sensor_type == self.expected_sensor_type
        
        return SensorData(
            gas_concentration=gas_concentration,
            sensor_type=sensor_type,
            temperature=temperature,
        )


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


