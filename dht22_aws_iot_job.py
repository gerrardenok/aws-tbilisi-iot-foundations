import time
import argparse
import json
import requests
from awscrt import io, mqtt
from awsiot import mqtt_connection_builder
from concurrent.futures import Future

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

# Initialize the AWS IoT Device SDK v2 for Python
event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)
client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

mqtt_connection = mqtt_connection_builder.mtls_from_path(
    endpoint=endpoint,
    cert_filepath=certificate,
    pri_key_filepath=private_key,
    ca_filepath=root_ca,
    client_bootstrap=client_bootstrap,
    on_connection_interrupted=None,
    on_connection_resumed=None,
    client_id=thing_name,
    clean_session=False,
    keep_alive_secs=6
)

# Connect to AWS IoT Core
connect_future = mqtt_connection.connect()
connect_future.result()
print(f"Client Connected")

def handle_job(topic, payload, **kwargs):
    jobconfig = json.loads(payload.decode('utf-8'))

    print(f"Job notification received at: {jobconfig['timestamp']}")

    if 'execution' in jobconfig:
        jobid = jobconfig['execution']['jobId']
        status = jobconfig['execution']['status']
        fileurl = jobconfig['execution']['jobDocument']['configfile']

        print(f"Job STATUS: {status}")

        print(f'File URL: {fileurl}')

        jobstatustopic = f'$aws/things/{thing_name}/jobs/{jobid}/update'

        time.sleep(2)

        print(f'Mark Job as IN_PROGRESS: PUB {jobstatustopic}')
        mqtt_connection.publish(topic=jobstatustopic, payload=json.dumps({"status": "IN_PROGRESS"}), qos=mqtt.QoS.AT_LEAST_ONCE)

        time.sleep(2)
        print(f'Dowloading config file the file from S3...')

        r = requests.get(fileurl)
        f = open("config.txt", "w")
        f.write(r.text)
        f.close()

        print(f'Config file config.txt successfully saved on FS!')

        time.sleep(1)
        print(f'Mark Job as SUCCEEDED: PUB {jobstatustopic}')
        mqtt_connection.publish(topic=jobstatustopic, payload=json.dumps({"status": "SUCCEEDED"}), qos=mqtt.QoS.AT_LEAST_ONCE)
        
        time.sleep(2)


jobnotifytopic = f'$aws/things/{thing_name}/jobs/notify-next'
print(f'Device waiting for the job: SUB {jobnotifytopic}')
subscribe_future, _ = mqtt_connection.subscribe(
    topic=jobnotifytopic,
    qos=mqtt.QoS.AT_LEAST_ONCE,
    callback=handle_job,
)

subscribe_result = subscribe_future.result()

input(f"Please enter to close the connection")

# Disconnect from AWS IoT Core
disconnect_future = mqtt_connection.disconnect()
disconnect_future.result()
print(f"Client Disconnected")
