# P1 to MQTT on Raspberry Pi

## [Domoticz](https://www.domoticz.com/) recieving P1 from USB and pushing MQTT

Domoticz is graphical, access from browser, maybe at 192.168.1.192:8080, it will probably tell when installing.

Add hardware in setup -> hardware. 

Add devices in setup -> devices. 

Select and push topics to MQTT in setup -> more options -> data push -> MQTT. 

See emulator and mosquitto below for conneciton details.

Use setup -> log to troubleshoot and utility to view domoticz's presentation of the data.

## [Mosquitto](https://mosquitto.org/) MQTT server

Default values are port 1883 at localhost, edit config to change.

A topic from domoticz will look like "given name"/index#/state so for example: domo/1/state.

You can publish and subscribe to topics. Use `mosquitto_sub -t "topic"` to see if anything's being pushed to some topic at the default connection. [Other flags](https://mosquitto.org/man/mosquitto_sub-1.html) for mosquitto_sub.


## The [emulator](https://github.com/jakob-ha/pop-p1/blob/main/p1emulator.py) and domoticz

The emulator writes to a simulated USB, for domoticz to recognize it it needs to be in /dev and be formatted as ttyUSB# for example /dev/ttyUSB99.

This can be accomplished with [socat](https://www.kali.org/tools/socat/#socat), example:

`sudo socat -d -d pty,raw,echo=0,mode=666,link=/dev/ttyUSB99 pty,raw,echo=0,mode=666,link=/dev/ttyUSB98`

Have the emulator write to one of the linked ports and domoticz read from the other. Note that this creates ports in /dev/pts with redirectors in /dev.

Be mindful of permissions, who runs domoticz? Is it the user or root? Who can access the ports? `ls -l /dev` & `ls -l dev/pts` if using socat. Raspberry OS has a Task Manager if you want to see that graphically.

The emulator writes once per second with baud rate 115200.

## The [anomaly chacking program](https://github.com/jakob-ha/pop-p1/blob/main/river.py)

This python program uses [river](https://pypi.org/project/river/) and [paho-mqtt](https://pypi.org/project/paho-mqtt/) to demonstrate subscription to an mqtt server and using that data with an anomaly detector.

Connection details are mosquitto's default.

The topics and message composition is specific and needs to be edited to fit what is being pushed by domoticz.

## Installations and dependencies

For python dependencies you may want to create a [venv](https://docs.python.org/3/library/venv.html) in your project directory to intall dependencies in.

python modules: pyserial paho-mqtt river

domoticz, mosquitto, socat

Maybe not exhaustive.

## Standards

[MQTT](https://mqtt.org/)

[DSMR 5.0.2](https://www.netbeheernederland.nl/publicatie/dsmr-502-p1-companion-standard)
