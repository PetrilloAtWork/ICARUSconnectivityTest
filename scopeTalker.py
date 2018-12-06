#!/usr/bin/env python

from stopwatch import WatchCollection
import visa
import numpy
from struct import unpack
import logging


class ScopeTalker:
  """Class managing the most common operations with out TDS 3054C oscilloscope.
  
  Example of interactive session:
  
  scope = ScopeTalker("192.168.230.29") # automatically connects
  print(scope.query("*IDN?"))
  
  scope.write('DATa:SOURce CH1')
  scope.write('DATa:ENCdg RPB')
  scope.write('DATa:WIDth 1')
  scope.write('DATa:STARt 1')
  scope.write('DATa:STOP 10000')
  
  VoltOffset = float(((scope.query('WFMPRE:YZERO?')).split(' '))[1])
  ADCtoVolt  = float(((scope.query('WFMPRE:YMULT?')).split(' '))[1])
  ADCoffset  = float(((scope.query('WFMPRE:YOFF?')).split(' '))[1])
  TimeStep   = float(((scope.query('WFMPRE:XINCR?')).split(' '))[1])
  
  scope.write('CURVE?')
  data = scope.read_raw()
  """
  def __init__(self, address, manager = None, connect = True, retries = 5):
    self.manager = manager if manager else visa.ResourceManager()
    self.address = address
    self.resourceID = 'TCPIP0::%s::INSTR' % self.address
    self.maxRetry = retries
    self.description = "<unknown>"
    self.scope = self.connect() if connect else None
  # __init__()
  
  def connect(self):
    try:
      self.scope = self.manager.open_resource(self.resourceID)
    except:
      logging.error("Exception raised while connecting to '{}'".format(self.resourceID))
      raise
    self.write("HEADer OFF") # don't include the header in the responses
    self.identify() # update description
    return self.scope
  # connect()
  
  def disconnect(self):
    if self.scope is None: return
    self.scope.close()
    self.scope = None
  # disconnect()
  
  def reconnect(self):
    self.disconnect()
    self.connect()
  # reconnect()
  
  ###
  ### direct access to the instrument
  ###
  def __call__(self): return self.scope
  
  ###
  ### infrastructure for class functionality (publicly available)
  ###
  def retry(self, call, *args):
    """Executes a `call` with specified arguments `args` until successful.
    
    At most `self.maxRetry` tries are attempted.
    """
    if isinstance(call, str):
      callname = call
      try: call = getattr(self.scope, callname)
      except AttributeError:
        raise RuntimeError("Instrument object does not have a call '{}'".format(callname))
    else:
      callname = call.__name__
    e = None
    for nRetry in self._retryLoop():
      try:
        return call(*args)
      except visa.VisaIOError as e:
        logging.error("Exception raised while running '{}' on '{}' [#{}]"
          .format(callname, self.resourceID, nRetry+1)
          )
    else:
      logging.error("Maximum number of retries ({}) reached trying to execute:\n"
        "{} {}.".format(self.maxRetry, callname, " ".join(map(repr, args))))
      raise e
    # for
  # retry()
  
  ###
  ### retry-able interface
  ###
  def query(self, queryString):
    return self.retry("query", queryString)
  
  def write(self, writeString):
    return self.retry("write", writeString)
  
  def read_raw(self):
    return self.retry("read_raw")
  
  def identify(self, cached = True):
    try: self.description = self.query("*IDN?").strip()
    except:
      if not cached: raise
    return self.description
  # identify()
  
  ###
  ### internal junk
  ###
  def _retryLoop(self): return self._tryUntil(self.maxRetry)
  
  @staticmethod
  def _tryUntil(n):
    i = 0
    while i < n:
      yield i
      i += 1
    else: raise StopIteration
  # _tryUntil()
  
# class ScopeTalker


################################################################################
class TDS3054Ctalker(ScopeTalker):
  """A `ScopeTalker` object with behaviour specific of Tektronix 3054C.
  
  """
  
  MaxChannels = 4
  WaveformSamples = 10000
  
  def __init__(self, *args, **kargs):
    ScopeTalker.__init__(self, *args, **kargs)
    self.timers = WatchCollection(
      'setup',
      'readout',
      'convert',
      'readData',
      title="Timing of `TDS3054Ctalker.readData()`",
      )
  # __init__()
  
  def readDataSetup(self):
    """Sets all channels for reading waveforms, and reads their settings.
    
    This function should be called just before a sequence of `readData()` calls.
    """
    with self.timers['setup']:
      self.calibration = {}
      for iChannel in range(self.MaxChannels):
        channel = "CH{}".format(iChannel + 1)
        self.write(
          'DATa:SOURce {channel};'   # select the channel
          ' ENCdg SRPBinary;'        # little endian, unsigned
          ' WIDth 1;'                # one byte per point (may be 2, that is 9 bits)
          ' STARt 1;'                # read the whole waveform: points 1 to 10000
          ' DATa:STOP {points}'
          .format(channel=channel, points=TDS3054Ctalker.WaveformSamples)
          )
        
        self.calibration[channel] = {
          'VoltOffset': float(((self.query('WFMPRE:YZERO?')).split(' '))[-1]),
          'ADCtoVolt':  float(((self.query('WFMPRE:YMULT?')).split(' '))[-1]),
          'ADCoffset':  float(((self.query('WFMPRE:YOFF?' )).split(' '))[-1]),
          'TimeStep':   float(((self.query('WFMPRE:XINCR?')).split(' '))[-1]),
          }
      # for
  # readDataSetup()
  
  def readData(self, channel):
    """Read the specified channel from the oscilloscope.
    
    It returns a pair of `numpy` array objects representing the sampling time
    [seconds] and the corresponding sampled voltage [volt].
    
    """
    with self.timers['readData']:
      
      if not isinstance(channel, str): channel = "CH{:d}".format(channel)
      assert(channel.startswith("CH"))
      
      calibrationInfo = self.calibration[channel]
      
      with self.timers['setup']:
        # most of setup is performed by `readDataSetup()`
        self.write('DATa:SOURce ' + channel)
      # setup
      
      with self.timers['readout']:
        self.write('CURVE?')
        data = self.read_raw()
      # readout
      
      with self.timers['convert']:
        #the value for 13 accounts for and removes :CURV #510000
        ADC_wave = self.blockData(data)
        
        ADC_wave = numpy.array(unpack('%sB' % len(ADC_wave), ADC_wave))

        #this is units of volts and milliseconds
        Volts = calibrationInfo['VoltOffset'] \
          + (ADC_wave - calibrationInfo['ADCoffset']) * calibrationInfo['ADCtoVolt']
        
        TimeStep = calibrationInfo['TimeStep']
        Time = numpy.arange(0.0, TimeStep * len(Volts), TimeStep)
      # convert
      
      return (Time, Volts)
    # with
  # readData()
  
  
  @staticmethod
  def blockData(block):
    """The format of a block is:
    
    #<S><size><data><EOL>
    
    where '#' is the literal '#' character, <S> is a numeric character
    representing the number of characters compounding <size>, <size> is a
    numerical string representing how many characters are in the data,
    <data> is the data in a string of <size> characters and <EOL> is a
    end-of-line terminator (should be '\n').
    """
    # remove the header from the block (if any)
    block = block[block.index('#'):]
    sizeSize = int(block[1])
    startData = 2 + sizeSize
    dataSize = int(block[2:startData])
    expectedSize = startData + dataSize + 1
    if expectedSize != len(block):
      logging.warning("Expected {} bytes in a data block, got {}",
        expectedSize, len(block)
        )
    # if
    return block[startData:-1]
  # blockData()
  
  
  def printTimers(self, out = logging.info):
    out(self.timers.toString(unit="ms", options=('times', 'average')))
  # printTimers()
  
  
# class TDS3054Ctalker


################################################################################
