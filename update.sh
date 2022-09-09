cd ..
rm master.zip
wget "https://github.com/moralmunky/SmartRent-MQTT-Bridge/archive/refs/heads/master.zip"
unzip -o master.zip
cp smartrent.env SmartRent-MQTT-Bridge-master/smartrent.env
cd SmartRent-MQTT-Bridge-master
docker build . -t smartrent-mqtt-bridge