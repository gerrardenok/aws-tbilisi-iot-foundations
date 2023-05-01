import requests
import argparse
import json
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

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

# Initiate the AWS IoT MQTT Shadow client
mqtt_client = AWSIoTMQTTClient(thing_name)
mqtt_client.configureEndpoint(endpoint, 8883)
mqtt_client.configureCredentials(root_ca, private_key, certificate)

# Connect to AWS IoT Core
mqtt_client.connect()
print(f"Client Connected")

def HandleJob(client, userdata, message):
       
    jobconfig = json.loads(message.payload.decode('utf-8'))

    print(f"Job notification received at: {jobconfig['timestamp']}")
       
    if 'execution' in jobconfig:
       
        jobid = jobconfig['execution']['jobId']
        status = jobconfig['execution']['status']
        fileurl = jobconfig['execution']['jobDocument']['configfile']

        print(f"Job STATUS: {status}")

        print(f'File URL: {fileurl}')
           
        jobstatustopic = "$aws/things/"+thing_name+"/jobs/"+ jobid + "/update"

        print(f'Mark Job as IN_PROGRESS: {jobstatustopic}')
        mqtt_client.publish(jobstatustopic, json.dumps({ "status" : "IN_PROGRESS"}),0)
           
        r = requests.get(fileurl)
        f = open("config.txt", "w")
        f.write(r.text)
        f.close()

        print(f'Mark Job as SUCCEEDED: {jobstatustopic}')   
        mqtt_client.publish(jobstatustopic, json.dumps({ "status" : "SUCCEEDED"}),0)
       
      
print('Device waiting for the job')
mqtt_client.subscribe("$aws/things/"+thing_name+"/jobs/notify-next", 1, HandleJob)

input("Please enter to close the connection\n")

mqtt_client.disconnect()
print("Client Disconnected\n")