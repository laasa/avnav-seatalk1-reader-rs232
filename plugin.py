import serial, time, socket, signal, sys, threading, queue
import errno
import fcntl
import os
import select
import struct
import sys
import termios


class Plugin:
  FILTER = []
  PATHDBT = "gps.STALK1_DBT"
  PATHSTW = "gps.STALK1_STW"
  CONFIG=[
    {
      'name': 'device',
      'description': 'set to the device path (alternative to usbid)',
      'default': '/dev/ttyUSB_SeatalkInp'
    },
    {
      'name': 'usbid',
      'description': 'set to the usbid of the device (alternative to device)',
      'default': ''
    },
    {
      'name': 'debuglevel',
      'description': 'set to the debuglevel',
      'default': '0'
    }
  ]
  @classmethod
  def pluginInfo(cls):
    """
    the description for the module
    @return: a dict with the content described below
            parts:
               * description (mandatory)
               * data: list of keys to be stored (optional)
                 * path - the key - see AVNApi.addData, all pathes starting with "gps." will be sent to the GUI
                 * description
    """
    return {
      'description': 'seatalk 1 protocol generator',
      'config': cls.CONFIG,
      'data': [
        {
          'path': cls.PATHDBT,
          'description': 'deepth below transducer',
        },
        {
          'path': cls.PATHSTW,
          'description': 'speed trough water',
        },
      ]
    }

  def __init__(self,api):
    """
        initialize a plugins
        do any checks here and throw an exception on error
        do not yet start any threads!
        @param api: the api to communicate with avnav
        @type  api: AVNApi
    """
    self.api = api # type: AVNApi
    #we register an handler for API requests
    self.lastReceived=0
    self.isConnected=False
    self.fd = None
    self.device=None
    self.debuglevel=None
    self.isBusy=False
    self.condition=threading.Condition()
    if hasattr(self.api,'registerEditableParameters'):
      self.api.registerEditableParameters(self.CONFIG,self._changeConfig)
    if hasattr(self.api,'registerRestart'):
      self.api.registerRestart(self._apiRestart)
    self.changeSequence=0
    self.startSequence=0

    self.queue = queue.Queue()

  def _apiRestart(self):
    self.startSequence+=1
    self.changeSequence+=1

  def _changeConfig(self,newValues):
    self.api.saveConfigValues(newValues)
    self.changeSequence+=1

  def getConfigValue(self,name):
    defaults=self.pluginInfo()['config']
    for cf in defaults:
      if cf['name'] == name:
        return self.api.getConfigValue(name,cf.get('default'))
    return self.api.getConfigValue(name)

  def run(self):
    startSequence=self.startSequence
    while startSequence == self.startSequence:
      try:
        #only AvNav after 20210224
        self.api.deregisterUsbHandler()
      except:
        pass
      self.runInternal()

  def runInternal(self):
    """
    the run method
    this will be called after successfully instantiating an instance
    this method will be called in a separate Thread
    The plugin sends every 10 seconds the depth value via seatalk
    @return:
    """
    changeSequence=self.changeSequence
    seq=0
    self.api.log("started")
    self.api.setStatus('STARTED', 'running')
    enabled=self.getConfigValue('enabled')
    if enabled is not None and enabled.lower()!='true':
      self.api.setStatus("INACTIVE", "disabled by config")
      return
    usbid=None
    try:
      self.device=self.getConfigValue('device')
      self.debuglevel=self.getConfigValue('debuglevel')
      usbid=self.getConfigValue('usbid')
      if usbid == '':
        usbid=None
      if self.device == '':
        self.device=None
      if self.device is None and usbid is None:
        raise Exception("missing config value device or usbid")

      if self.device is not None and usbid is not None:
        raise Exception("only one of device or usbid can be set")
    except Exception as e:
      self.api.setStatus("ERROR", "config error %s "%str(e))
      while changeSequence == self.changeSequence:
        time.sleep(0.5)
      return
    if usbid is not None:
      self.api.registerUsbHandler(usbid,self.deviceConnected)
      self.api.setStatus("STARTED", "using usbid %s, baud=4800" % (usbid))
    else:
      self.api.setStatus("STARTED","using device %s, baud=4800"%(self.device))
    connectionHandler=threading.Thread(target=self.handleConnection, name='seatalk-remote-connection')
    connectionHandler.setDaemon(True)
    connectionHandler.start()
    while changeSequence == self.changeSequence:
      #if not self.isConnected:
        #return {'status': 'not connected'}
      source='internal'

      try:
        item = self.queue.get(block=True, timeout=10)
        data = item.split("\r")
        self.api.debug("Read from queue: '" + str(data[0]) + "'")
        darray = data[0].split(",")
        if ( darray[0] == '$STALK' ):

            ''' DPT: 00  02  YZ  XX XX  Depth below transducer: XXXX/10 feet'''
            if((darray[1] == '00') and (darray[2] == '02') and (darray[3] == '00')):
              rt={}
              value=int('0x' + str(darray[4]),base=16) + (int('0x'+ str(darray[5]), base=16)*255)
              self.api.debug("Get DBT SEATALK frame: " + str(value) + "'")
              rt['DBT'] = float(value or '0') / (10.0 * 3.281)
              self.api.addData(self.PATHDBT, rt['DBT'],source=source)
              record="$AADPT,%.1f,%.1f,"%(float(rt['DBT']),float(0.0))
              self.api.addNMEA(record,addCheckSum=True,omitDecode=False,source=source)
              self.api.debug("=> NMEA: " + str(record))

            ''' STW: 20  01  XX  XX  Speed through water: XXXX/10 Knots'''
            if((darray[1] == '20') and (darray[2] == '01')):
              rt={}
              value=int('0x' + str(darray[3]),base=16) + (int('0x'+ str(darray[4]), base=16)*255)
              self.api.debug("Get STW SEATALK frame: " + str(value) + " (0x" + str(darray[4]) +  str(darray[3]) + ")")
              rt['STW'] = ((float(value or '0') / 10.0) * 1.852) / 3.6
              self.api.addData(self.PATHSTW, rt['STW'],source=source)

      #VHW - Water speed and heading

      #        1   2 3   4 5   6 7   8 9
      #        |   | |   | |   | |   | |
      # $--VHW,x.x,T,x.x,M,x.x,N,x.x,K*hh<CR><LF>

      # Field Number:
      #  1) Degress True
      #  2) T = True
      #  3) Degrees Magnetic
      #  4) M = Magnetic
      #  5) Knots (speed of vessel relative to the water)
      #  6) N = Knots
      #  7) Kilometers (speed of vessel relative to the water)
      #  8) K = Kilometers
      #  9) Checksum

      except Exception as e:
        self.api.error("unable to read from queue: " + str(e))
        self.api.addData(self.PATHDBT, float('0'),source=source)
        self.api.addData(self.PATHSTW, float('0'),source=source)
        pass

  def handleConnection(self):
    self.api.log("handleConnection")
    changeSequence=self.changeSequence
    errorReported=False
    lastDevice=None
    while changeSequence == self.changeSequence:
      if self.device is not None:
        if self.device != lastDevice:
          self.api.setStatus("STARTED", "trying to connect to %s at 4800" % (self.device))
          lastDevice=self.device
        #on windows we would need an integer as device...
        try:
          pnum = int(self.device)
        except:
          pnum = self.device

        self.isConnected=False
        self.isBusy=False
        try:
          self.fd = os.open(self.device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
          #fcntl.fcntl(self.fd, fcntl.F_SETFL, os.FNDELAY)
          #fcntl.fcntl(self.fd, fcntl.F_SETFL, os.O_NONBLOCK)

          # some systems support an extra flag to enable the two in POSIX unsupported
          # paritiy settings for MARK and SPACE
          CMSPAR = 0  # default, for unsupported platforms, override below
          plat = sys.platform.lower()
          if plat[:5] == 'linux':    # Linux (confirmed)  # noqa
            # extra termios flags
            CMSPAR = 0o10000000000  # Use "stick" (mark/space) parity
            self.api.log("Running on Linux: that is good")
          else:
            self.api.error("Need Linux as platform")

          ''' Here is the tricky part: Setting parity to SPACE, but want to get paraty errors'''
          orig_attr = termios.tcgetattr(self.fd)
          iflag, oflag, cflag, lflag, ispeed, ospeed, cc = orig_attr
          ''' set 8 data bits, sticky parity with parity bit reset (SPACE)'''
          ispeed=ospeed=termios.B4800
          cflag &= ~(termios.CBAUD | termios.CBAUDEX | termios.CSIZE | termios.PARENB  | termios.PARODD | termios.CRTSCTS | termios.CSTOPB)
          cflag |=  (termios.B4800 | termios.CS8 | termios.CLOCAL | termios.CREAD | termios.PARENB | CMSPAR)
          lflag &= ~(termios.ICANON | termios.ECHO | termios.ECHOE | termios.ECHOK | termios.ECHONL | termios.ISIG | termios.IEXTEN)
          ''' enable marking data with bad parity '''
          iflag &= ~(termios.INLCR | termios.IGNCR | termios.ICRNL | termios.BRKINT | termios.IGNBRK | termios.IUCLC | termios.IGNPAR | termios.INPCK | termios.ISTRIP | termios.IXON | termios.IXOFF | termios.IXANY)
          iflag |=  (termios.PARMRK | termios.INPCK)
          oflag &= ~(termios.OPOST | termios.ONLCR | termios.OCRNL)
          ''' Wait for up to 1s (10 deciseconds), returning as soon as any data is received.'''
          cc[termios.VTIME] = 10
          cc[termios.VMIN]  = 0
          termios.tcsetattr(self.fd, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])

        except Exception as e:
            self.api.setStatus("ERROR","unable to connect/connection lost to %s: %s"%(self.device, str(e)))
            self.api.error("unable to connect/connection lost to %s: %s" % (self.device, str(e)))

        self.api.setStatus("NMEA","connected to %s at 4800"%(self.device))
        self.api.log("connected to %s at 4800" % (self.device))
        self.isConnected=True
        data=list()
        while True:
            try:
              timeout = 1
              ready, _, _ = select.select([self.fd], [], [], 1)
              if ready:
                data0 = os.read(self.fd, 1)
                if(int(self.debuglevel) > 0):
                  self.api.log("read byte: 0x"+ str(hex(data0[0])))
                if (data0[0] == 0xff):
                  if((len(data) == 0) or (data[-1]!=0xff)):
                    data.append(data0[0])
                else:
                  if((len(data) > 0) and (data[-1]==0xff)):
                    if(len(data) > 0):
                      data = data[:-1]
                      dataout="$STALK,"
                      for x in data:
                        string1=str(hex(x))
                        data1=str(string1[2:])
                        if(len(data1)==1):
                          data1="0"+data1
                        dataout=dataout+data1+","

                      if(int(self.debuglevel) > 0):
                        self.api.log("send STALK frame: " + str(dataout))
                      dataout=dataout+"\r\n"
                      self.queue.put(dataout)

                    data.clear()
                  else:
                    data.append(data0[0])

            except Exception as e:
                # this is for Python 3.x where select.error is a subclass of
                # OSError ignore BlockingIOErrors and EINTR. other errors are shown
                # https://www.python.org/dev/peps/pep-0475.
                #if e.errno not in (errno.EAGAIN, errno.EALREADY, errno.EWOULDBLOCK, errno.EINPROGRESS, errno.EINTR):
                self.api.setStatus("ERROR","???? to %s: %s"%(self.device, str(e)))
                self.api.error("???? %s: %s" % (self.device, str(e)))
                self.isConnected=False
                pass

            if( (changeSequence != self.changeSequence) or (self.isConnected==False)):
                os.close(self.fd)
                break

        time.sleep(1)

        if(changeSequence != self.changeSequence):
          break;

      time.sleep(1)
