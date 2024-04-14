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

