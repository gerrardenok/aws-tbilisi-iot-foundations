import time
import Adafruit_DHT
import argparse
import json
from awscrt import io, mqtt
from awsiot import mqtt_connection_builder

# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--endpoint', help='AWS IoT Core endpoint')
parser.add_argument('--certificates', help='Path to the certificates folder')
parser.add_argument('--interval', type=int, help='Interval of sending data in seconds', default=1)
args = parser.parse_args()

# AWS IoT Core settings
thing_name = 'dht22_aws_iot_shadow'
endpoint = args.endpoint
root_ca = f'{args.certificates}/root-ca.pem'
private_key = f'{args.certificates}/private.pem.key'
certificate = f'{args.certificates}/certificate.pem.crt'

# Configure DHT22 sensor
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 21  # GPIO 21

# Initialize send_data flag
send_data = False

# Set QoS level 1
QoS = mqtt.QoS.AT_LEAST_ONCE

# Initialize the IoT SDK
event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)
client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

# Create a MQTT connection
mqtt_connection = mqtt_connection_builder.mtls_from_path(
    endpoint=endpoint,
    cert_filepath=certificate,
    pri_key_filepath=private_key,
    client_bootstrap=client_bootstrap,
    ca_filepath=root_ca,
    on_connection_interrupted=None,
    on_connection_resumed=None,
    client_id=thing_name,
    clean_session=False,
    keep_alive_secs=6
)

# Connect to AWS IoT Core
connect_future = mqtt_connection.connect()
connect_future.result()
print('Connected to AWS IoT Core')

# Function to handle shadow get response
def on_shadow_get_response(topic, payload, dup, qos, retain, **kwargs):
    global send_data
    payload_dict = json.loads(payload)
    desired_state = payload_dict.get('state', {}).get('desired', {})
    send_data = desired_state.get('send_data', False)
    print(f'Initial send_data state: {send_data}')

# Subscribe to shadow get response topic
shadow_get_response_topic = f'$aws/things/{thing_name}/shadow/get/accepted'
subscribe_future, packet_id = mqtt_connection.subscribe(
    topic=shadow_get_response_topic,
    qos=QoS,
    callback=on_shadow_get_response
)
subscribe_result = subscribe_future.result()

# Request current shadow state
shadow_get_topic = f'$aws/things/{thing_name}/shadow/get'
mqtt_connection.publish(
    topic=shadow_get_topic,
    payload='',
    qos=QoS
)

# Wait for the initial state to be loaded
time.sleep(2)

# Function to read data from the DHT22 sensor
def read_dht22_data():
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    return humidity, temperature

# Function to handle shadow updates
def on_shadow_delta_received(topic, payload, dup, qos, retain, **kwargs):
    global send_data
    payload_dict = json.loads(payload)
    desired_state = payload_dict['state']
    if 'send_data' in desired_state:
        send_data = desired_state['send_data']

# Subscribe to shadow updates
shadow_delta_topic = f'$aws/things/{thing_name}/shadow/update/delta'
subscribe_future, packet_id = mqtt_connection.subscribe(
    topic=shadow_delta_topic,
    qos=mqtt.QoS.AT_LEAST_ONCE,
    callback=on_shadow_delta_received
)
subscribe_result = subscribe_future.result()

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
                shadow_update_topic = f'$aws/things/{thing_name}/shadow/update'
                if send_data:
                    mqtt_connection.publish(
                        topic=shadow_update_topic,
                        payload=payload,
                        qos=QoS
                    )
                    print(f'Published: {payload}')
            else:
                print('Failed to read sensor data.')
        else:
            print('Idle...')
        time.sleep(args.interval)
except KeyboardInterrupt:
    print('Interrupted: Disconnecting MQTT connection...')
    disconnect_future = mqtt_connection.disconnect()
    disconnect_future.result()
