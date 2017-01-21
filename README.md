# HomeBrite LED Bulb Gateway for SmartThings Hub

The ST hub cannot control BLE devices so this lets you create a bridge using a CHIP or RPI3 that is discoverable via SSDP.

## Setup

First, use the mobile app to create a pin and add all of your lights to a group.

## Install controller on CHIP/RPI with systemd

```
sudo apt-get install -y python-twisted libglib2.0-dev
sudo pip install -r requirements.txt
```

```
cat > csrmesh_lights.env <<"EOF"
BLE_ADDRESSES=SPACE_SEPARATED_LIST_OF_MACS
BLE_PIN=INSERT_YOUR_4_DIGIT_PIN
EOF
sudo mv csrmesh_lights /etc/csrmesh_lights.env
```

```
sudo cp csrmesh-lights.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable csrmesh-lights
sudo systemctl start csrmesh-lights
```
