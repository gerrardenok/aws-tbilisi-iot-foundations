import time
import Adafruit_DHT
import argparse
import json
from datetime import datetime
from awscrt import io, mqtt
from awsiot import mqtt_connection_builder

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
DHT_PIN = 21  # GPIO 21

# Initialize flags
send_data = False
exit_script = False

# Set QoS level 1
QoS = mqtt.QoS.AT_LEAST_ONCE

# Callback when connection is accidentally lost.
def on_connection_interrupted(connection, error, **kwargs):
    global exit_script
    if error.name == "AWS_ERROR_MQTT_UNEXPECTED_HANGUP":
        print(f'Connection interrupted with AWS_ERROR_MQTT_UNEXPECTED_HANGUP. Exiting...')
        exit_script = True
    else:
        print(f'Connection interrupted. error: {error}')

# Callback when an interrupted connection is re-established.
def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print(f'Connection resumed. return_code: {return_code} session_present: {session_present}')

    if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
        print('Session did not persist. Resubscribing to existing topics...')
        resubscribe_future, _ = connection.resubscribe_existing_topics()

        resubscribe_future.add_done_callback(on_resubscribe_complete)

def on_resubscribe_complete(resubscribe_future):
    resubscribe_results = resubscribe_future.result()
    print(f'Resubscribed with results: {resubscribe_results}')

# Function to read data from the DHT22 sensor
def read_dht22_data():
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    return humidity, temperature

# Callback for when a message is received
def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    print(f"Received message from topic '{topic}': {payload}")
    global send_data

    if topic == 'dht22/cmd/start':
        send_data = True
        print('Starting data transmission...')
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        ack_payload = json.dumps({'timestamp': timestamp})
        mqtt_connection.publish(
            topic='dht22/cmd/start/ack',
            payload=ack_payload,
            qos=QoS
        )
    elif topic == 'dht22/cmd/stop':
        send_data = False
        print('Stopping data transmission...')
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        ack_payload = json.dumps({'timestamp': timestamp})
        mqtt_connection.publish(
            topic='dht22/cmd/stop/ack',
            payload=ack_payload,
            qos=QoS
        )

# Initialize the IoT SDK
event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)
client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

# Configure Last Will and Testament message
last_will_payload = '{"status": "disconnected"}'
last_will = mqtt.Will(
    topic="dht22/status",
    payload=last_will_payload.encode('utf-8'),
    qos=QoS,
    retain=False
)

# Initiate the AWS IoT MQTT connection
mqtt_connection = mqtt_connection_builder.mtls_from_path(
    endpoint=args.endpoint,
    cert_filepath=certificate,
    pri_key_filepath=private_key,
    client_bootstrap=client_bootstrap,
    ca_filepath=root_ca,
    on_connection_interrupted=on_connection_interrupted,
    on_connection_resumed=on_connection_resumed,
    client_id=client_id,
    clean_session=False,
    keep_alive_secs=6,
    will=last_will
)

# Subscribe to control topics
print(f"Connecting to {args.endpoint} with client ID '{client_id}'...")

connect_future = mqtt_connection.connect()

# Wait for connection to be established.
connect_future.result()
print("Connected!")

# Subscribe to control topics
print("Subscribing to 'dht22/cmd/start' and 'dht22/cmd/stop'")
subscribe_future, _ = mqtt_connection.subscribe(
    topic='dht22/cmd/start',
    qos=QoS,
    callback=on_message_received
)

subscribe_future, _ = mqtt_connection.subscribe(
    topic='dht22/cmd/stop',
    qos=QoS,
    callback=on_message_received
)

subscribe_future.result()
print("Subscribed!")

# Main loop to send data to AWS IoT Core every X seconds
while True:
    if exit_script:
        break

    if send_data:
        humidity, temperature = read_dht22_data()
        if humidity is not None and temperature is not None:
            timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            payload = json.dumps({
                'temperature': round(temperature, 2),
                'humidity': round(humidity, 2),
                'timestamp': timestamp
            })
            if send_data:
                mqtt_connection.publish(
                    topic='dht22/data',
                    payload=payload,
                    qos=QoS
                )
                print(f'Published: {payload}')
        else:
            print('Failed to read sensor data.')
    else:
        print('Idle...')
    time.sleep(args.interval)