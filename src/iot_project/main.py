import os

import trio

from .sunfounder_picar.picarx_control import car_control_loop
from .gas_sensors.gas_monitoring_system import MonitoringSystem


async def main():
    import dotenv

    # Load environment variables from .env file
    dotenv.load_dotenv()

    # Get MongoDB-URI
    mongo_uri = os.getenv("MONGODB_URI")

    system = MonitoringSystem(mongo_uri)

    with system:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(car_control_loop)
            nursery.start_soon(system.main_task)


if __name__ == "__main__":
    trio.run(main)
