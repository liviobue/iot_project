

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
WorkingDirectory=/home/missd/Desktop/IoT-Project/iot_project/src
Environment="MONGODB_URI=mongodb://<mongo-uri>"
ExecStart=/home/missd/.pyenv/versions/3.12.1/bin/python -m iot_project.main
Restart=on-failure


[Install]
WantedBy=multi-user.target




## Enable Service-File
```bash
sudo systemctl daemon-reload                     
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

