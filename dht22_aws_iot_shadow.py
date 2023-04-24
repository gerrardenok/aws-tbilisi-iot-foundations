import sys
import time
import Adafruit_DHT
import argparse
import boto3
import json
from datetime import datetime
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient

# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--endpoint', help='AWS IoT Core endpoint')
parser.add_argument('--certificates', help='Path to the certificates folder')
parser.add_argument('--interval', type=int, help='Interval of sending data in seconds', default=1)
args = parser.parse_args()

# Initialize send_data flag
send_data = False

# AWS IoT Core settings
thing_name = 'dht22_aws_iot_shadow'
endpoint = args.endpoint
root_ca = f'{args.certificates}/root-ca.pem'
private_key = f'{args.certificates}/private.pem.key'
certificate = f'{args.certificates}/certificate.pem.crt'

# Configure DHT22 sensor
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 14  # GPIO 14

# Initiate the AWS IoT MQTT Shadow client
shadow_client = AWSIoTMQTTShadowClient(thing_name)
shadow_client.configureEndpoint(endpoint, 8883)
shadow_client.configureCredentials(root_ca, private_key, certificate)

shadow_client.configureAutoReconnectBackoffTime(1, 32, 20)
shadow_client.configureConnectDisconnectTimeout(10)
shadow_client.configureMQTTOperationTimeout(5)

# Connect to AWS IoT Core
shadow_client.connect()

# Create a shadow handler
shadow_handler = shadow_client.createShadowHandlerWithName(thing_name, False)

# Function to read data from the DHT22 sensor
def read_dht22_data():
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    return humidity, temperature

# Function to handle shadow updates
def shadow_delta_callback(payload, responseStatus, token):
    global send_data
    payload_dict = json.loads(payload)
    desired_state = payload_dict['state']
    if 'send_data' in desired_state:
        send_data = desired_state['send_data']

# Subscribe to shadow updates
shadow_handler.shadowRegisterDeltaCallback(shadow_delta_callback)

# Load initial state of send_data from Shadow
def shadow_get_callback(payload, response_status, token):
    global send_data
    payload_dict = json.loads(payload)
    desired_state = payload_dict.get('state', {}).get('desired', {})
    send_data = desired_state.get('send_data', False)
    print(f'Initial send_data state: {send_data}')

shadow_handler.shadowGet(shadow_get_callback, 5)
time.sleep(2)

# Main loop to send data to AWS IoT Core every X seconds
try:
    while True:
        if send_data:
            humidity, temperature = read_dht22_data()
            if humidity is not None and temperature is not None:
                payload = json.dumps({
                    'state': {
                        'reported': {
                            'temperature': round(temperature, 2),
                            'humidity': round(humidity, 2)
                        }
                    }
                })
                shadow_handler.shadowUpdate(payload, None, 5)
                print(f'Published: {payload}')
            else:
                print('Failed to read sensor data.')
        else:
            print('Idle...')
        time.sleep(args.interval)
except KeyboardInterrupt:
    print('Interrupted: Disconnecting shadow client...')
    shadow_client.disconnect()
    print('Shadow client disconnected. Exiting.')
