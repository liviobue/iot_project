
# Python-Environment
Python 3.12.1


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
python -m iot_project.main
```


# Ordner-Struktur
## Electronic:
- PCB-Designs
- Output für die Produktion
- Übersicht über die Board-Tests

## NodeRed
- Alle Flows in NodeRed

## Notebooks
- Jupyter Notebooks mit Prototyp-Code
- Jupyter Notebook mit vereinfachtem Code fürs Elektronik-Testing

## Presentation
- Vor-Präsentation
- Präsentation

## src/iot_project
- Code für die verschiedenen Teile der Software