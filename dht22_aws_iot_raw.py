import sys
import time
import Adafruit_DHT
import argparse
import boto3
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

# Configure DHT22 sensor
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 14  # GPIO 14

# Initiate the AWS IoT MQTT client
mqtt_client = AWSIoTMQTTClient(client_id)
mqtt_client.configureEndpoint(endpoint, 8883)
mqtt_client.configureCredentials(root_ca, private_key, certificate)

mqtt_client.configureAutoReconnectBackoffTime(1, 32, 20)
mqtt_client.configureOfflinePublishQueueing(-1)
mqtt_client.configureDrainingFrequency(2)
mqtt_client.configureConnectDisconnectTimeout(10)
mqtt_client.configureMQTTOperationTimeout(5)

# Connect to AWS IoT Core
mqtt_client.connect()

# Function to read data from the DHT22 sensor
def read_dht22_data():
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    return humidity, temperature

# Send data to AWS IoT Core every X seconds
while True:
    humidity, temperature = read_dht22_data()
    if humidity is not None and temperature is not None:
        payload = f'{{"temperature": {temperature:.2f}, "humidity": {humidity:.2f}}}'
        mqtt_client.publish('dht22/data', payload, 1)
        print(f'Published: {payload}')
    else:
        print('Failed to read sensor data.')
    time.sleep(args.interval)

mqtt_client.disconnect()
