# avnav-seatalk1-reader-rs232


# General

The plugin read seatalk 1 protocol via configured RS232.

It is widely based on the
- seatalk remote plugin (https://github.com/wellenvogel/avnav-seatalk-remote-plugin),
- more nmea plugin      (https://github.com/kdschmidt1/avnav-more-nmea-plugin) and
- Seatalk1 to NMEA 0183 (https://github.com/MatsA/seatalk1-to-NMEA0183/blob/master/STALK_read.py).

There exist the way to activate the GPIO plugin in openplotter/signalk base on 'Seatalk1 to NMEA 0183'.
But especially for beginners like me it's possibly a bit to complicate to get knowledge 
- which software serve the hardware, 
- which one is storing the value and 
- what is the way to get these values in avnav.

It takes a bit of time to understand the powerful ideas of multiplexing between all the software in openplotter family.
To get in touch with avnav plugin programming and python and to have simple and short data ways I tried another way.
Especially the last thing could be interesting: To have the most current 'depth below transducer' value and not the 2 seconds old one.

# Parameter

- device: e.g. '/dev/ttyUSB0'
- usbid: as alternative for devive name

# Details

# Hardware needs
It is commended to use optocoupler between seatalk 1 level and RS232 inputs.

An example for such an circuit is suggested here: http://www.thomasknauf.de/rap/seatalk3.htm

![grafik](https://user-images.githubusercontent.com/98450191/153572739-ca93722a-7c4f-4cb3-abc5-d087621b8b64.png)

When needing more then 1 optical inputs (e.g. 3 for anchor chain counter) it make sense to use an module like BUCCK_817_4_V1.0.
![grafik](https://user-images.githubusercontent.com/98450191/153612142-9221c6fb-b963-413a-9dd8-ecab960d3dd3.png)

Inside the Seatalk1 data line I have added an additional Resistor of 1K and couple both signals (Seatalk 1 Data, GND) via pin 1&2 on a 5-pin-socket.
Pin 3,4 and 5 of these socket are used for anchor chain counter (reed contact, up , down).

![grafik](https://user-images.githubusercontent.com/98450191/153612080-9d67fe77-6967-4da9-a12f-5b9174ac2a88.png)


# Software installation

To install this plugin please 
- install packages via: sudo apt-get update && sudo apt-get install python3-serial
- start pigpio deamon e.g. via sudo servive pigdiod restart
- create directory '/usr/lib/avnav/plugins/avnav-seatalk1-reader-rs232' and 
- and copy the file plugin.py to this directory.

# Using in anvav
- STW: value from gps.SEATALK_STW in [m/s]

![grafik](https://user-images.githubusercontent.com/98450191/153569250-92ccd43b-df36-41cf-88ca-6f6340052a29.png)

- DBT: value from gpc.SEATALK_DBT in [m]

![grafik](https://user-images.githubusercontent.com/98450191/153557342-b5453d97-4b93-4f32-a148-b5365c5bd431.png)

# TODOs
- generate NMEA0183 frames (for multiplexing to other openplotter software like signalk) ?
