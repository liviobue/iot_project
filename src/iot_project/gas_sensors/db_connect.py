import contextlib

import pymongo
import numpy as np


@contextlib.contextmanager
def connect_to_db(mongodb_uri):
    """Open the connection to the DB and return the collection
    Create collection with unique index, if there is not yet one"""

    with pymongo.MongoClient(mongodb_uri) as DBclient:
        db = DBclient["IoT-Project"]
        yield db["Raw-Data"]


def represent_for_mongodb(obj):
    match obj:
        case dict():
            return {
                represent_for_mongodb(k): represent_for_mongodb(v)
                for k, v in obj.items()
            }
        case tuple() | list():
            return type(obj)(represent_for_mongodb(v) for v in obj)
        case np.generic():
            return obj.item()
        case _:
            return obj
