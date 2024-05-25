mac adresse: d8:3a:dd:83:37:5c 



# Get Started:


## How to install
Execute this from the Repository-Root
```bash
pip install -e .
```


## How to run the sensor measurement only:

Create `.env`-file with `MONGO_URI` containing the connectionstring to your IoT-Database.

Then, run:
```bash
python -m iot_project.gas_monitoring_system
```


