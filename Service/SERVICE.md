# Service-File

## Create Service-File
```bash
sudo nano /etc/systemd/system/iot_project.service
```


## Service-File
[Unit]
Description=IoT Project Service
After=multi-user.target

[Service]
Type=simple
User=missd
WorkingDirectory=/home/missd/Desktop/IoT-Project/iot_project/
ExecStart=/home/missd/.pyenv/versions/3.12.1/bin/python -m iot_project.main
Restart=on-failure

[Install]
WantedBy=multi-user.target



## Reload Service-File
```bash
sudo systemctl daemon-reload                     
```


## Enable Service-File
```bash                 
sudo systemctl enable iot_project.service
```


## Start Service-File
```bash
sudo systemctl start iot_project.service
```


## Check Status of Service-File
```bash
journalctl -u iot_project.service 
```
(jump to the end with SHIFT+g)

