import typing
import json
import asyncio
import mitmproxy.websocket
import paho.mqtt.client as mqtt
import ssl
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import datetime

#######################################################


MQTT_HOST = os.environ.get('MQTT_HOST')
MQTT_PORT = int(os.environ.get('MQTT_PORT'))
MQTT_USER = os.environ.get('MQTT_USER')
MQTT_PASS = os.environ.get('MQTT_PASS')
MQTT_TLS = bool(os.environ.get('MQTT_TLS'))
MQTT_TOPIC_PREFIX = os.environ.get('MQTT_TOPIC_PREFIX')

devices = json.loads(os.environ.get('DEVICES'))

#######################################################
topics = {}
ws_message = ''

# def on_mqtt_connect(self, client, userdata, flags, rc=None):
#     print("Connected to MQTT broker with result code " + str(rc))
def on_mqtt_connect(client, userdata, flags, rc):
    if rc==0:
        print("MQTT connected OK Returned code=",rc)
    else:
        print("MQTT Bad connection Returned code=",rc)
        # 0: Connection successful
        # 1: Connection refused    ^`^s incorrect protocol version
        # 2: Connection refused    ^`^s invalid client identifier
        # 3: Connection refused    ^`^s server unavailable
        # 4: Connection refused    ^`^s bad username or password
        # 5: Connection refused    ^`^s not authorised

mqtt_client = mqtt.Client(transport="websockets")
mqtt_client.username_pw_set(MQTT_USER, password=MQTT_PASS)
#removing gets rid of [SSL: WRONG_VERSION_NUMBER] wrong version number (_ssl.c:1051) error even though set to false
# if MQTT_TLS is True:
#     mqtt_client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
#     mqtt_client.tls_insecure_set(not MQTT_TLS)
mqtt_client.on_connect = on_mqtt_connect
print(devices)
print(mqtt_client.__dict__)

class SmartRentBridge:
    ws_message = ''

    def __init__(self):
        mqtt_client.on_message = self.on_mqtt_message
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
        mqtt_client.loop_start()
        for key, value in devices.items():
            topics[value[1]] = [key, value[2]]
            if value[2] == "thermostat":
                for postfix in ['target', 'mode', 'fan_mode']:
                    topic = f'{MQTT_TOPIC_PREFIX}/{value[1]}/{postfix}/set'
                    print(f'Subscribing to {topic}')
                    mqtt_client.subscribe(topic)
            if value[2] == "lock":
                print('subscribing to lock')
                mqtt_client.subscribe(MQTT_TOPIC_PREFIX + '/' + value[1] + '/set')

    async def inject(self, flow: mitmproxy.websocket.WebSocketFlow):
        joined = False
        while not flow.ended and not flow.error:
            if not joined:
                print("Sending join to smartrent to init connection to devices")
                for key, value in devices.items():
                    intiStr = f'[{value[3]}, {value[3]}, "devices:{key}", "phx_join", {{}}]'
                    print(intiStr)
                    flow.inject_message(flow.server_conn, intiStr)
                joined = True

            if len(self.ws_message) > 0:
                print("Attempting to inject message")
                print(self.ws_message)
                flow.inject_message(flow.server_conn, str(self.ws_message))
                self.ws_message = ''
            await asyncio.sleep(2)

    def on_mqtt_message(self, client, userdata, msg):
        print(f'Got MQTT message: {msg.topic}')

        topic = msg.topic.split('/')
        device_id = str(topics[topic[1]][0])
        device_type = topics[topic[1]][1]
        command = topic[2]
        deviceChannel = str(devices[str(device_id)][3])
        value = msg.payload.decode().lower()
        
        # Handle Thermostat Commands
        if device_type == "thermostat":
            print('Updating thermostat')
            if command == "mode":
                self.ws_message = f'["{deviceChannel}","null","devices:{device_id}","update_attributes",{{"device_id":"{device_id}","attributes":[{{"name":"mode","value":"{value}"}}]}}]'
            if command == "target":
                self.ws_message = f'["{deviceChannel}","null","devices:{device_id}","update_attributes",{{"device_id":"{device_id}","attributes":[{{"name":"cooling_setpoint","value":"{value}"}},{{"name":"heating_setpoint","value":"{value}"}}]}}]'
            if command == "fan_mode":
                self.ws_message = f'["{deviceChannel}","null","devices:{device_id}","update_attributes",{{"device_id":"{device_id}","attributes":[{{"name":"fan_mode","value":"{value}"}}]}}]'
        
        # Handle Lock Commands
        if device_type == "lock":
            print('Updating lock')
            self.ws_message = f'["{deviceChannel}","null","devices:{device_id}","update_attributes",{{"device_id":"{device_id}","attributes":[{{"name":"locked","value":"{value}"}}]}}]'

    #####
    def websocket_start(self, flow):
        asyncio.get_event_loop().create_task(self.inject(flow))

    def websocket_message(self, flow: mitmproxy.websocket.WebSocketFlow):
        message = flow.messages[-1]
        self.parse_message(message.content)

    def parse_message(self, message):
        message_json = json.loads(message)
        msg_type = message_json[3]
        msg_data = message_json[4]
        
        if msg_type == 'phx_reply':
            status = msg_data.get('status')
            if status == 'ok':
                with open("last_heartbeat", "w") as f:
                    f.write(str(datetime.datetime.now().timestamp()))
                print("Heartbeat")
                    
        if msg_type == "attribute_state":
            attribute = msg_data['name']
            device_id = str(msg_data['device_id'])
            #device_id = int(message_json[2].split(":")[1])
            device_id = str(message_json['device_id'])
            value = msg_data['last_read_state']
            # Thermostat Setpoint
            if attribute in ["heating_setpoint", "cooling_setpoint"]:
                mqtt_client.publish(MQTT_TOPIC_PREFIX + '/' + devices[device_id][1] + '/target', payload=value, qos=1, retain=True)
            if attribute == "current_temp":
                mqtt_client.publish(MQTT_TOPIC_PREFIX + '/' + devices[device_id][1] + '/current', payload=value, qos=1, retain=True)
            # Thermostat Mode
            if attribute == "mode":
                mqtt_client.publish(MQTT_TOPIC_PREFIX + '/' + devices[device_id][1] + '/mode', payload=value, qos=1, retain=True)
            if attribute == "fan_mode":
                mqtt_client.publish(MQTT_TOPIC_PREFIX + '/' + devices[device_id][1] + '/fan_mode', payload=value, qos=1, retain=True)
            ######################
            # Lock State
            if attribute == "locked":
                print(device_id)
                mqtt_client.publish(MQTT_TOPIC_PREFIX + '/' + devices[device_id][1] + '/status', payload=value, qos=1, retain=True)
                print(MQTT_TOPIC_PREFIX + '/' + devices[device_id][1] + '/status')
                print("Payload: " + value)
            if attribute == "notifications":
                mqtt_client.publish(MQTT_TOPIC_PREFIX + '/' + devices[device_id][1] + '/detail', payload=value, qos=1, retain=True)
                print(MQTT_TOPIC_PREFIX + '/' + devices[device_id][1] + '/detail')
                print("Payload: " + value)
        print(message)
        return


addons = [SmartRentBridge()]