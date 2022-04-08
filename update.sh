rm master.zip
wget "https://github.com/moralmunky/SmartRent-MQTT-Bridge/archive/refs/heads/main.zip"
unzip -o master.zip
cp smartrent.env SmartRent-MQTT-Bridge/smartrent.env
cd SmartRent-MQTT-Bridge                      
docker build . -t smartrent-mqtt-bridge