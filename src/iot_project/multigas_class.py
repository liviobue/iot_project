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

bk.io.output_notebook()
%autoawait trio



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