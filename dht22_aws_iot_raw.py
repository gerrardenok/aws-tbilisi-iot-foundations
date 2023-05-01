import time
import Adafruit_DHT
import argparse
import json
from datetime import datetime
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--endpoint', help='AWS IoT Core endpoint')
parser.add_argument('--certificates', help='Path to the certificates folder')
parser.add_argument('--interval', type=int, help='Interval of sending data in seconds', default=1)
args = parser.parse_args()

# AWS IoT Core settings
client_id = 'dht22_aws_iot_raw'
endpoint = args.endpoint
root_ca = f'{args.certificates}/root-ca.pem'
private_key = f'{args.certificates}/private.pem.key'
certificate = f'{args.certificates}/certificate.pem.crt'
QoS = 0


# Configure DHT22 sensor
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 21  # GPIO 21

# Initiate the AWS IoT MQTT client
mqtt_client = AWSIoTMQTTClient(client_id)
mqtt_client.configureEndpoint(endpoint, 8883)
mqtt_client.configureCredentials(root_ca, private_key, certificate)

mqtt_client.configureAutoReconnectBackoffTime(1, 32, 20)
mqtt_client.configureOfflinePublishQueueing(-1)
mqtt_client.configureDrainingFrequency(2)
mqtt_client.configureConnectDisconnectTimeout(10)
mqtt_client.configureMQTTOperationTimeout(5)

# Configure Last Will and Testament message
last_will_payload = '{"status": "disconnected"}'
mqtt_client.configureLastWill('dht22/status', last_will_payload, QoS)

# Function to read data from the DHT22 sensor
def read_dht22_data():
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    return humidity, temperature

# Function to handle start command
def start_handler(client, userdata, message):
    global send_data
    send_data = True
    print('Starting data transmission...')
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    ack_payload = json.dumps({'timestamp': timestamp})
    mqtt_client.publish('dht22/cmd/start/ack', ack_payload, QoS)

# Function to handle stop command
def stop_handler(client, userdata, message):
    global send_data
    send_data = False
    print('Stopping data transmission...')
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    ack_payload = json.dumps({'timestamp': timestamp})
    mqtt_client.publish('dht22/cmd/stop/ack', ack_payload, QoS)

# Connect to AWS IoT Core
mqtt_client.connect()
mqtt_client.subscribe('dht22/cmd/start', 1, start_handler)
mqtt_client.subscribe('dht22/cmd/stop', 1, stop_handler)

# Initialize send_data flag
send_data = False

# Main loop to send data to AWS IoT Core every X seconds
while True:
    if send_data:
        humidity, temperature = read_dht22_data()
        if humidity is not None and temperature is not None:
            timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            payload = json.dumps({
                'temperature': round(temperature, 2),
                'humidity': round(humidity, 2),
                'timestamp': timestamp
            })
            mqtt_client.publish('dht22/data', payload, QoS)
            print(f'Published: {payload}')
        else:
            print('Failed to read sensor data.')
    else:
        print('Idle...')
    time.sleep(args.interval)