# HomeBrite LED Bulb Gateway for SmartThings Hub

The ST hub cannot control BLE devices so this lets you create a bridge using a CHIP or RPI3 that is discoverable via SSDP.

## Setup

First, make sure you use the HomeBrite mobile app to create a pin and add all of your lights to a group.

### Install bridge on Raspberry Pi 3 with resin.io

Create an account and new device on [resin.io](http://resin.io), download the ResinOS to your RPI3.

```
git remote add resin username@git.resin.io:username/devicename.git
```

> replace username and devicename with your own

```
git push resin master
```

### (non resin.io) Install with systemd

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

### or with docker-compose on HypriotOS with RPI3

Install [HypriotOS](https://blog.hypriot.com/downloads/) on your Raspberry Pi 3

```
git clone https://github.com/danisla/iot-homebrite-led-bulb.git
```

```
cd iot-homebrite-led-bulb
cat > .env <<"EOF"
BLE_MAC=SPACE SEPARATED MAC ADDRESS LIST
BLE_PIN=YOUR_PIN
DEVICE_INDEX=1
HTTP_PORT=8282
EOF
```

```
docker-compose pull
docker-compose up -d
```

## Add to SmartThings app

From the [SmartThings developer portal](graph.api.smartthings.com), add the devicetype and control app groovy sources found in the [`./smartthings`](./smartthings) directory. Make sure to publish them after copy-pasting.

From the SmartThings mobile app, goto Marketplace -> SmartApps -> My Apps and add the `RESTful CSRMesh Dimmable Light` app.

Search for your hub then add it. The device will appear under `Things` with the `ip:port` as the name, rename it to something friendly like "Bedroom lights" and optionally add it to a room.
