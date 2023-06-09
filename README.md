# AWS Tbilisi User Group - IoT Foundations

This repository contains a demos in Python for a presentation on IoT (Internet of Things) titled ["Introduction to IoT Foundations - Kickstart Your Journey with AWS."](https://www.meetup.com/aws-tbilisi/events/293215777/) The presentation will be delivered by Mikhail Vataleu on Thursday, May 11th at a meetup in Tbilisi organized by @Klika Tech and @AWS User Group Meetup.

## Presentation Slides

- [PDF](./slides.pdf)
- [PPTX](./slides.pptx)

## Prerequisites

- Raspberry Pi 4 with Raspbian OS installed
- DHT22 sensor connected to the Raspberry Pi 4
- Python 3 installed
- AWS IoT Core setup with certificates

## Installation

1. Clone this repository:

```
git https://github.com/gerrardenok/aws-tbilisi-iot-foundations.git
```

2. Change to the repository directory:

```
cd aws-tbilisi-iot-foundations
```

3. Install the required Python packages:

```
pip install -r requirements.txt
```

## Usage

Run the script with the desired command-line arguments for the path to the certificates and the interval of sending data:

```bash
python dht22_aws_iot_raw.py --endpoint ${YOUR_AWS_IOT_ENDPOINT} --certificates /path/to/certificates --interval 5
```

If the arguments are not given, the script sets the interval to 1 second:

```bash
python dht22_aws_iot_raw.py
```

The script will continuously read data from the DHT22 sensor and publish the temperature and humidity measurements to the `dht22/data` topic in AWS IoT Core. You can use AWS IoT Core to process, store, or visualize this data in various ways.

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.