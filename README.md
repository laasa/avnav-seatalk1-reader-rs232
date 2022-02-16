# avnav-seatalk1-reader-rs232
![grafik](https://user-images.githubusercontent.com/98450191/153623654-01c26f56-17bb-4a65-a76a-2ed3d991d7aa.png)

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

There is the need to convert seatalk 1 level to RS232 levels.
An example for such an circuit is suggested here: http://www.thomasknauf.de/rap/seatalk3.htm

![grafik](https://user-images.githubusercontent.com/98450191/153572739-ca93722a-7c4f-4cb3-abc5-d087621b8b64.png)

Another idea is to use optocoupler between boat and PC.

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

# Known Issues
- only tested with linux
- Windows want work caused by missing defines for CMSPAR
- CMSPAR is needed to use the sticky parity bit functionality

# TODOs
- generate NMEA0183 frames (for multiplexing to other openplotter software like signalk) ?

# Helpers
Setup the serial devices by their serial numbers
- Label your first USB serial device (e.g SeatalkOut)
- Connect the first USB serial device to the PC
- Get the vendorID, deviceID and serial number of the tty device (here "/dev/ttyUSB0")
   udevadm info -a -n /dev/ttyUSB0 | grep {idVendor} | head -n1  => ATTRS{idVendor}=="0403" 
   udevadm info -a -n /dev/ttyUSB0 | grep {bcdDevice} | head -n1 => ATTRS{bcdDevice}=="0600"
   udevadm info -a -n /dev/ttyUSB0 | grep {serial} | head -n1    => ATTRS{serial}=="A10KKBM3"
- creates an udev rule
  mcedit sudo mcedit /etc/udev/rules.d/10-local.rules
   SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="A10KKBM3", MODE="0666", SYMLINK+="ttyUSB_SeatalkOut"
- Continue with the next devices
- at the end the file /etc/udev/rules.d/10-local.rules may look like that
    SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="A10KKF9V", MODE="0666", SYMLINK+="ttyUSB_SeatalkInp"
    SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="A10KKBM3", MODE="0666", SYMLINK+="ttyUSB_SeatalkOut"
- Use this names in avnav (e.g: "/dev/ttyUSB_SeatalkInp")

