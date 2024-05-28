# Information about the Project

## Python-Environment
Python 3.12.1



## Project-Structure
### Electronic:
- PCB-Designs
- Output für die Produktion
- Übersicht über die Board-Tests

### NodeRed
- Alle Flows in NodeRed

### Notebooks
- Jupyter Notebooks mit Prototyp-Code
- Jupyter Notebook mit vereinfachtem Code fürs Elektronik-Testing

### Presentation
- Vor-Präsentation
- Präsentation

### Service
- Information zum Service-File, um die Software automatisch beim Boot des Raspberry Pi's zu starten

### src/iot_project
- Code für die verschiedenen Teile der Software




## Get started manually:
### How to install
Execute this from the Repository-Root
```bash
pip install -e .
```

### How to run the sensor measurement only:
Create `.env`-file with `MONGO_URI` containing the connectionstring to your IoT-Database.
Then, run:
```bash
python -m iot_project.main
```