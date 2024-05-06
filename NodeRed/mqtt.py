import paho.mqtt.publish as publish
import time
 
MQTT_SERVER = "127.0.0.1"
MQTT_OXYG   = "sensor/o2"
MQTT_MONO   = "sensor/co"
MQTT_AMMO   = "sensor/nh3"

def read_o2():
    t = 02.read_all().gas_concentration
    t = round(t)
    return t

def read_co():
    h = co.read_all().gas_concentration
    h = round(h)
    return h

def read_nh3():
    p = NH3.read_all().gas_concentration
    p = round(p)
    return p

o2 = " Oxigen: " + str(read_o2())
co = " Humidity:    " + str(read_co())
nh3 = " Pressure:    " + str(read_nh3())

for i in range(100):
    publish.single(MQTT_OXYG, o2, hostname=MQTT_SERVER)

    publish.single('sensor/o2', o2, hostname='127.0.0.1')

    time.sleep(1)
    publish.single(MQTT_MONO, co, hostname=MQTT_SERVER)
    time.sleep(1)
    publish.single(MQTT_AMMO, nh3, hostname=MQTT_SERVER)
    time.sleep(1)

import paho.mqtt.client as mqtt
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
client.connect("172.20.10.3", 1880, 60)