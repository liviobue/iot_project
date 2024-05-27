import datetime
import os

import trio
import anyio
import numpy as np

from .multigas_sensors import MultiGasSensor, SensorType
from .alert_handling import AlertManager
from .db_connect import connect_to_db, represent_for_mongodb

i2cbus = 1
NH3_ADDRESS = 0x75
CO_ADDRESS = 0x76
O2_ADDRESS = 0x77


class MonitoringSystem:

    def __init__(self, mongo_uri, *, measurement_interval=0.1, aggregation_interval=10):
        self.mongo_uri = mongo_uri
        self.alert_manager = AlertManager()
        self.measurement_interval = measurement_interval
        self.aggregation_interval = aggregation_interval
        self.sensors = dict(
            NH3=MultiGasSensor(i2cbus, NH3_ADDRESS, SensorType.NH3),
            CO=MultiGasSensor(i2cbus, CO_ADDRESS, SensorType.CO),
            O2=MultiGasSensor(i2cbus, O2_ADDRESS, SensorType.O2),
        )


    async def main_task(self):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.alert_manager.alert_loop)
            nursery.start_soon(self.measurement_loop)


    def __enter__(self):
        self.alert_manager.__enter__()


    def __exit__(self, type, value, tb):
        return self.alert_manager.__exit__(type, value, tb)


    def aggregate_data(self, alldata: list[tuple[float, float]]) -> dict[str, float]:
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


    async def measurement_loop(self):

        next_measurement = trio.current_time() + self.measurement_interval
        next_aggregation = trio.current_time() + self.aggregation_interval

        with connect_to_db(self.mongo_uri) as collection:

            while True:
                all_data = {k: [] for k in self.sensors}

                while trio.current_time() < next_aggregation:
                    try:
                        time = (
                            datetime.datetime.now()
                            .astimezone(None)
                            .astimezone(datetime.timezone.utc)
                        )
                        data = {
                            k: v.read_all().gas_concentration
                            for k, v in self.sensors.items()
                        }

                    except Exception as ex:
                        # print(f'{ex!r} - retry')
                        await trio.sleep(0.05)
                        continue

                    for k, v in data.items():
                        all_data[k].append((time, v))

                    self.alert_manager.check_alerts(
                        ammonia=data["NH3"],
                        carbon_monoxide=data["CO"],
                        oxygen=data["O2"],
                    )

                    await anyio.sleep_until(next_measurement)
                    next_measurement += self.measurement_interval

                # Aggregate Data
                next_aggregation += self.aggregation_interval
                
                for k, v in all_data.items():
                    if not v:
                        v=0
                    aggregation = {k: self.aggregate_data(v)}
                aggregation.update(time=time)

                collection.insert_one(represent_for_mongodb(aggregation))

                print(aggregation)


async def main():
    import dotenv

    # Load environment variables from .env file
    dotenv.load_dotenv()

    # Get MongoDB-URI
    mongo_uri = os.getenv("MONGODB_URI")

    system = MonitoringSystem(mongo_uri)

    with system:
        await system.main_task()


if __name__ == "__main__":
    trio.run(main)
