#!/usr/bin/env python

#
# from testDriver import * ; reader = ChimneyReader("EW00", fake=True) ; reader.start()
# reader.next()
# 

__doc__ = """
Interactive driver for the scope reader.

So far, only python environment stuff is usable interactively
(see `ChimneyReader`), but running from python is still quite better.
"""

################################################################################
### default settings


################################################################################
### importing and default setup
import drawWaveforms
from stopwatch import StopWatch
from scopeTalker import TDS3054Ctalker
import numpy
import random
import sys
import re
import os
import logging

# set verbosity level to `INFO`; not all output has been converted to `logging`
# this value is reset by `ChimneyReader`.
logging.getLogger().setLevel(logging.INFO)


################################################################################
### general utilities

def confirm(msg, yes="Y", no="N", caseSensitive=False):
  options = []
  if isinstance(yes, str): yes = [ yes, ]
  elif yes is None: yes = []
  if yes: options.append(yes[0])
  if isinstance(no, str): no = [ no, ]
  elif no is None: no = []
  if no: options.append(no[0])
  print "%s [%s] " % (msg, "/".join(options)),
  
  caseProc = (lambda s:s) if caseSensitive else str.lower
  yesAnswers = map(caseProc, yes)
  noAnswers = map(caseProc, no)
  while True:
    try: Answer = sys.stdin.readline().strip()
    except KeyboardInterrupt:
      if no: print no[0]
      return False
    answer = caseProc(Answer)
    if answer in yesAnswers: return True
    if answer in noAnswers: return False
  # while
  assert False
# confirm()


################################################################################
### Reader state: describes what we are doing right now (incomplete)

class ReaderState:
  
  ChimneyMatcher = re.compile('[EW]{2}[0-9]{1,2}')
  CableMatcher = re.compile('[A-Z][0-9]{2}')
  
  def __init__(self):
    self.enabled = False
    self.confirm = True
    self.chimney = None
    self.cableTag = None
    self.cableNo = None
    self.position = None
    self.N = 10
    
    self.quiet = False
    self.fake = False
  # __init__()
  
  def enable(self):
    print "All commands are now going to be executed for real."
    self.enabled = True
  def disable(self):
    print "All commands are now just being printed and NOT going to be executed."
    self.enabled = False
  
  @staticmethod
  def isChimney(chimney):
    return ReaderState.ChimneyMatcher.match(chimney.upper()) is not None
  
  @staticmethod
  def isCable(cable):
    return ReaderState.CableMatcher.match(cable.upper()) is not None
  
  def cable(self): return "%(cableTag)s%(cableNo)02d" % vars(self)
  
  def firstIndex(self):
    return drawWaveforms.WaveformSourceInfo.firstIndexOf(self.position, self.N)
  
  def stateStr(self):
    return "Chimney %(chimney)s connection %(cableTag)s%(cableNo)02d position %(position)d" % vars(self)
  
  def execute(self, command):
    if self.enabled:
      if self.confirm:
        yesKey = str(random.randint(0, 9))
        print "Run: '%s'? [<%s>,<Enter> for yes] " % (command, yesKey),
        answer = sys.stdin.readline().strip()
        if answer != yesKey:
          print "(chickened out)"
          return
      # if confirm
      print "$ " + command
    else:
      print "$ " + command
    # if ... else
  # execute()
  
  def makeWaveformSourceInfo(self, channelNo = None, index = None):
    return drawWaveforms.WaveformSourceInfo(
      chimney=self.chimney, connection=self.cable(), channelIndex=channelNo,
      position=self.position, index=index
      )
  # makeWaveformSourceInfo()
  
# class ReaderState


################################################################################
### ChimneyReader: helper with functions for a DAQ workflow

class ChimneyReader:
  """
  
  `ChimneyReader` now controls the communication with the oscilloscope, via a
  `ScopeTalker` object (in fact, a `TDS3054Ctalker` object).
  
  
  """
  CableTags = { 'EE': 'V', 'EW': 'S', 'WE': 'V', 'WW': 'S', }
  
  MinPosition = 1
  MaxPosition = 8
  MinCable = 1
  MaxCable = 18
  
  WaveformFilePattern = drawWaveforms.WaveformSourceFilePath.StandardPattern
  WaveformDirectory = drawWaveforms.WaveformSourceFilePath.StandardDirectory
  
  class ConfigurationError(RuntimeError):
    def __init__(self, msg, *args, **kargs):
      RuntimeError.__init__(self, "Configuration error: " + msg, *args, **kargs)
  # ConfigurationError
  
  def __init__(self,
   configurationFile,
   chimney = None,
   IP = None, N = None, fake = None
   ):
    """Creates a new `ChimneyReader`.
    
    This object *requires* a configuration file, although most of the options
    have default values which kick in if no configuration is provided.
    Also, the additional arguments override the values in the configuration
    file.
    """
    params = self._configure(configurationFile)
    
    # override configuration parameters with specified arguments
    if IP is not None: params.IP = IP
    if fake is not None: params.fake = fake
    if N is not None: params.N = N
    
    # if ROOT is not available, we don't plot anything
    try: ROOT
    except NameError: self.drawWaveforms = False
    
    self.scope = TDS3054Ctalker(params.IP, connect=not params.fake)
    self.readerState = ReaderState()
    self.readerState.chimney = chimney
    self.readerState.N = params.N
    self.setQuiet(True) # this will be one day removed
    self.setFake(params.fake)
    self.canvas = None
    self.timers = {
      'readout': StopWatch(startNow=False),
      'setup'  : StopWatch(startNow=False),
      'channel': StopWatch(startNow=False),
      'writing': StopWatch(startNow=False),
      } # timers
  # __init__()
  
  
  def _configure(self, configurationFilePath):
    """Reads a configuration file and sets values accordingly.
    
    See the following code (starting at "=== BEGIN CONFIGURATION PARSING ==="
    below) for the "documentation" of the file format.
    
    Where configuration values directly pertain class attributes, those
    attributes are directly set. In the other cases, configuration values are
    extracted and stored in an unfeatured object and returned to the caller for
    processing.
    """
    from configparser import SafeConfigParser, NoSectionError, NoOptionError
    configFile = SafeConfigParser()
    configFile.read(configurationFilePath)
    
    class ConfigParams: pass
    localParams = ConfigParams()
    
    class OptionDefault:
      def __init__(self, config, section = None):
        self.config = config
        self.section = section
      def pickSection(self, section): self.section = section
      def __call__(self, *args): return self.get(*args)
      def get(self, option, *args):
        return self._getDispatcher('get', option, *args)
      def str(self, option, *args): return self.get(options, *args)
      def int(self, option, *args):
        return self._getDispatcher('getint', option, *args)
      def bool(self, option, *args):
        return self._getDispatcher('getboolean', option, *args)
      def _getDispatcher(self, getterName, option, *args):
        assert len(args) <= 1
        return (self._getWithDefault if len(args) == 1 else self._get) \
          (option, *args[:1], getterName=getterName)
      def _get(self, option, getterName = 'get'):
        return getattr(self.config, getterName)(self.section, option)
      def _getWithDefault(self, option, default, getterName = 'get'):
        if self.config is None or self.section is None: return default
        try: return self._get(option, getterName)
        except (NoSectionError, NoOptionError): return default
    # class OptionDefault
    
    getConfig = OptionDefault(configFile)
    
    # === BEGIN CONFIGURATION PARSING ==========================================
    #
    # [Oscilloscope] section: oscilloscope parameters and settings
    #
    getConfig.pickSection('Oscilloscope')
    
    #
    # IP address to connect to; oscilloscope will be addressed as 
    # `TPCIP0:<IP>:instr`
    # This parameter is mandatory.
    # This option can be overridden in `ChimneyReader` constructor.
    localParams.IP = getConfig('Address')
    
    
    #
    # [Reader] section: general `ChimneyReader` options
    #
    getConfig.pickSection('Reader')
    
    #
    # Verbosity: the level of verbosity assigned to `logging` messages
    # Default is 'INFO'
    logLevelTag = getConfig('Verbosity', 'INFO').upper()
    try:
      logLevel = getattr(logging, logLevelTag)
    except AttributeError:
      raise ConfigurationError(
        "Verbosity level '{}' is not supported by `logging` module."
        .format(logLevelTag)
        )
    try: logLevel = int(logLevel)
    except ValueError:
      raise ConfigurationError(
        "`logging.{}` is {}, not a verbosity level."
        .format(logLevelTag, logLevel)
        )
    logging.debug \
      ("Setting verbosity level to: {} ({})".format(logLevel, logLevelTag))
    logging.getLogger().setLevel(logLevel)
    
    #
    # WaveformsPerChannel: number of waveforms acquired on each position and
    #                      channel
    # Default is 10.
    localParams.N = getConfig.int('WaveformsPerChannel', 10)
    
    #
    # FakeMode: whether fake mode is activated.
    #           With fake mode on, no connection to the oscilloscope is opened,
    #           and read data is fake.
    # Default is OFF.
    # This option can be overridden in `ChimneyReader` constructor.
    localParams.fake = getConfig.bool('FakeMode', False)
    
    #
    # DrawWaveforms: whether to draw the waveforms just acquired
    # Default is ON, unless ROOT module is not loaded.
    self.drawWaveforms = getConfig.bool('DrawWaveforms', True)
    
    
    #
    # [Storage] section: parameters for moving acquired data to storage
    #
    getConfig.pickSection('Storage')
    
    #
    # Server: the remote node to connect to for transferring data.
    # Destination: the directory where to write in the remote node
    # User: the user name used for logging in the remote node
    # 
    # The generated script transfers data with a command like:
    #     
    #     rsync <Source> <User>@<Server>:<Destination>/
    #     
    # These parameters are optional.
    # If <Server> is not specified, no script will ever be generated.
    # If <User> is not specified, `<User>@` part of the command is omitted.
    # If <Destination> is not specified, `/<Destination>` part of the command is
    # omitted.
    localParams.storage = ConfigParams()
    localParams.storage.server = getConfig('Server', None)
    localParams.storage.outputDir = getConfig('Destination', None)
    localParams.storage.user = getConfig('RemoteUser', None)
    
    # === END CONFIGURATION PARSING ============================================
    
    return localParams
  # readConfigurationFile()
  
  
  @staticmethod
  def usage():
    print """
    Create a new instance of `ChimneyReader` with:
        
        reader = ChimneyReader(chimney='EW15')
        
    then to set up the data acquisition do:
        
        reader.start()
        
    (or you can set the channel as argument of `start()`).
    Then, each time you run:
        
        reader.next()
        
    you read a new position/cable in ascending position sequence and descending
    cable sequence.
    In the future will be possible to remove the previous reading with
    `removeLast()`.
    """
  # usage()
  
  def setQuiet(self, quiet = True): self.readerState.quiet = quiet
  def setFake(self, fake = True): self.readerState.fake = fake
  
  def start(self, chimney = None, N = None):
    
    if N is not None: self.readerState.N = N
    if chimney is not None: self.readerState.chimney = chimney
    if self.readerState.chimney is None:
      raise RuntimeError("\"start()\"... which chimney??")
    if not self.readerState.isChimney(self.readerState.chimney):
      raise RuntimeError("%r is not a valid chimney." % self.readerState.chimney)
    
    ChimneyReader.resetReaderState(readerState=self.readerState)
    
    self.sourceSpecs = self.setupSourceSpecs()
    
    # here we assume that (1) `waveformInfo` is complete enough for the
    # directory name and (2) that name is common to all the files
    tempDir = ChimneyReader.tempDirName(self.sourceSpecs.sourceInfo)
    try: os.makedirs(tempDir)
    except os.error: pass # it exists, which is actually good
    logging.info("Output for this chimney will be written into: '{}'".format(tempDir))
    
    self.printNext()
  # start()
  
  def readout(self):
    # We try to avoid code duplication: since some code putting together file
    # names already exists in `drawWaveforms`, we use code from there.
    # The file name composing code relies on a "state" which is a superset of
    # when is included in `ReaderState` (except for `N`): we use that state
    # (`WaveformSourceInfo` object) to track the state internally.
    # Note that here the state that is also in `readerState` is not changed.
    
    
    waveformInfo = self.readerState.makeWaveformSourceInfo()
    waveformInfo.setFirstIndex(N=self.readerState.N)
    self.sourceSpecs.setSourceInfo(waveformInfo)
    
    with self.timers['readout'], self.timers['setup']:
      self.scope.readDataSetup()
    
    for iSet in range(self.readerState.N):
      for iChannel in range(waveformInfo.MaxChannels):
        
        with self.timers['readout']:
          
          #
          # set the state
          #
          channelNo = iChannel + 1
          waveformInfo.setChannelIndex(channelNo)
          
          with self.timers['channel']:
            #
            # read the data from the oscilloscope
            #
            Time, Volt = (
              self.scope.readData(waveformInfo.channelIndex)
              if not self.readerState.fake
              else (
                numpy.arange(0.0, 1.0E-5 * self.scope.WaveformSamples, 1.0E-5),
                numpy.arange(0.0, 1.0E-6 * self.scope.WaveformSamples, 1.0E-6),
              ))
          # with readout
          
          with self.timers['writing']:
            #
            # save it in a file
            #
            waveformFilePath = self.currentWaveformFilePath()
            self.writeWaveform(waveformFilePath, Time, Volt)
          # with writing
          
        # with readout
      # for channels
      waveformInfo.increaseIndex()
    # for waveform set number
  # readout()
  
  def currentWaveformFilePath(self): return self.sourceSpecs.buildPath()
  
  def writeWaveform(self, waveformFilePath, Time, Volt):
    """Writes `Time` and `Volt` information into a CSV file `waveformFilePath`.
    
    The two data structures are expected to be numpy iterables.
    """
    
    nSamples = 0
    with open(waveformFilePath, 'w+') as file_:
      for values in zip(numpy.nditer(Time), numpy.nditer(Volt)):
        print >>file_, ",".join([ "%g" ] * len(values)) % values
        nSamples += 1
      # for
    # with
    logging.info("Written {} points into '{}'".format(nSamples, waveformFilePath))
  # writeWaveform()
  
  
  def printNext(self):
    if self.readerState.chimney is None:
      print "You'd better set a chimney first."
      return False
    if self.readerState.cableNo is None or self.readerState.position is None:
      print "No test next."
      return False
    print "next(): %s" % self.readerState.stateStr()
  # printNext()
  
  def skipToNext(self, n = 1):
    if self.readerState.position == self.MaxPosition:
      self.readerState.position = self.MinPosition
      if self.readerState.cableNo == self.MinCable:
        self.readerState.cableNo = None
        self.readerState.position = None
        return False
      else: self.readerState.cableNo -= 1
    else: self.readerState.position += 1
    if (n > 1) and not self.skipToNext(n-1): return False
    self.sourceSpecs.sourceInfo.connection = self.readerState.cable()
    self.sourceSpecs.sourceInfo.setPosition(self.readerState.position)
    return True
  # skipToNext()
  
  def skipToPrev(self, n = 1):
    if self.readerState.position == self.MinPosition:
      self.readerState.position = self.MaxPosition
      if self.readerState.cableNo == self.MaxCable:
        self.readerState.cableNo = None
        self.readerState.position = None
        return False
      else: self.readerState.cableNo += 1
    else: self.readerState.position -= 1
    if (n > 1) and not self.skipToPrev(n-1): return False
    self.sourceSpecs.sourceInfo.connection = self.readerState.cable()
    self.sourceSpecs.sourceInfo.setPosition(self.readerState.position)
    return True
  # skipToPrev()
  
  def readNext(self):
    self.readout()
    if self.drawWaveforms: self.plotLast()
    self.skipToNext()
    self.printNext()
  # readNext()
  next = readNext
  
  def listLast(self):
    return self.sourceSpecs.allPositionSources(N=self.readerState.N)
  
  def plotLast(self):
    # this will work only if `drawWaveforms` module is loaded
    
    self.canvas = drawWaveforms.plotAllPositionWaveforms(self.sourceSpecs, canvas=self.canvas)
    self.canvas.Update()
  # plotLast()
  
  def removeLast(self, n = 1):
    if not self.skipToPrev():
      print >>sys.sdterr, "There was no previous reading! now you did it."
      return False
    
    # remove data files
    dataFiles = self.listLast()
    if not confirm("Remove %d files from %s?" % (len(dataFiles), self.readerState.stateStr())):
      print "You're the boss."
      self.skipToNext()
      self.printNext()
      return False
    for path in dataFiles:
      if not os.path.exists(path):
        print >>sys.stderr, "Expected data file '%s' not found." % path
        continue
      try: os.remove(path)
      except IOError, e:
        print >>sys.stderr, "Failed to remove '%s': %s" % (filePath, e)
    # for
    
    if (n > 1) and not self.removeLast(n-1): return False
    if n == 1: self.printNext()
    return True
  # removeLast()
  
  def verify(self, outputDir = None, thoroughness = 1):
    """Scans the output directory finding if data files are missing or spurious.
    
    Only CSV files (ending in '.csv') are considered.
    
    Thoroughness level:
    - 0: check that the number of CSV files in the output directory is the right
         one (5760)
    - 1: check that there are no missing files
    - 2: check that there are no spurious files
    - 3: check that all the files have the expected number of lines each
    - 4: check that all the files are fully parseable
    """
    
    if self.readerState.chimney is None:
      logging.error("No chimney being parsed.")
      return False
    #
    # expected files
    #
    # we run though all expected reader states in a local loop:
    readerState = ChimneyReader.resetReaderState \
      (chimney=self.readerState.chimney, N=self.readerState.N)
    sourceSpecs = self.makeSourceSpecs(readerState)
    
    if not outputDir:
      outputDir = ChimneyReader.tempDirName(sourceSpecs.sourceInfo)
    expectedFiles = set()
    while True:
      positionFiles = sourceSpecs.allPositionSources(readerState.N)
      expectedFiles.update(positionFiles)
      
      if not ChimneyReader.incrementReaderState(readerState): break
      sourceSpecs.sourceInfo.connection = readerState.cable()
      sourceSpecs.sourceInfo.setPosition(readerState.position)
    # while
    logging.debug("Expected {nFiles} files in '{outputDir}'"
      .format(nFiles=len(expectedFiles), outputDir=outputDir)
      )
    
    #
    # detected files
    #
    if not os.path.isdir(outputDir):
      logging.error(
        "Expected {nFiles} files and, well, '{outputDir}' is not even a directory."
        .format(nFiles=len(expectedFiles), outputDir=outputDir)
        )
      return False
    # if
    CSVfiles = set()
    for file_ in os.listdir(outputDir):
      file_ = os.path.join(outputDir, file_)
      if not os.path.isfile(file_) or (os.path.splitext(file_)[-1] != '.csv'):
        continue
      CSVfiles.add(file_)
    # for
    logging.debug("Found {nFiles} CSV files in '{outputDir}'"
      .format(nFiles=len(CSVfiles), outputDir=outputDir)
      )
    
    success = True
    
    #
    # thoroughness >= 0: the right number of files
    # 
    
    if thoroughness == 0:
      if len(CSVfiles) == len(expectedFiles): return True
      else:
        logging.error(
          "Expected {nExpected} files in '{outputDir}', {nFound} found."
          .format(nExpected=len(expectedFiles), nFound=len(CSVfiles), outputDir=outputDir)
          )
        success = False
      # if ... else
    # if thoroughness == 0
    
    #
    # thoroughness >= 1: all needed files are there
    # 
    if thoroughness >= 1:
      missingFiles = expectedFiles - CSVfiles
      if missingFiles:
        logging.info("{nMissing} files missing:\n".format(nMissing=len(missingFiles))
          + "\n".join([ "[{}] '{}'".format(*fileInfo) for fileInfo in enumerate(sorted(missingFiles))])
          )
        logging.error("{nMissing}/{nExpected} files missing!".format(
          nMissing=len(missingFiles), nExpected=len(expectedFiles)
          ))
        success = False
      # if missing
    # if thoroughness >= 1
      
    #
    # thoroughness >= 2: no spurious CSV files are there
    # 
    if thoroughness >= 2:
      spuriousFiles = CSVfiles - expectedFiles
      if spuriousFiles:
        logging.info("{nSpurious} extra CSV files:\n".format(nSpurious=len(spuriousFiles))
          + "\n".join([ "[{}] '{}'".format(*fileInfo) for fileInfo in enumerate(sorted(spuriousFiles))])
          )
        logging.error("{nSpurious} spurious CSV files!".format(
          nSpurious=len(spuriousFiles)
          ))
        success = False
      # if missing
    # if thoroughness >= 2
    
    dataFiles = CSVfiles & expectedFiles
    
    # 
    # thoroughness >= 3
    # 
    if thoroughness >= 3:
      nExpectedPoints = self.scope.WaveformSamples
      for fileName in dataFiles:
        logging.debug("Checking: '{}'".format(fileName))
        unparseable = None
        nLines = 0
        with open(fileName, 'r') as f:
          for iLine, line in enumerate(f):
            # skip empty lines
            line = line.strip()
            if not line: continue
          
            # skip comments
            if line[0] == '#': continue
            
            nLines += 1
            # 
            # thoroughness >= 3: each file has the correct number of lines
            # 
            pass # just counting
            
            #
            # thoroughness >= 4: all files are parseable
            # 
            if thoroughness >= 4:
              if unparseable is None:
                try:
                  # try converting everything
                  tokens = map(float, map(str.strip, line.strip().split(",")))
                except ValueError:
                  logging.debug(
                    "Line '{fileName}':{line} is not parseable: '{content}'".format(
                    fileName=fileName, line=iLine, content=line
                    ))
                  unparseable = iLine
              if unparseable is None:
                if len(tokens) != 2:
                  logging.debug(
                    "Line '{fileName}':{line} has {nTokens} tokens: '{content}'".format(
                    fileName=fileName, line=iLine, nTokens=len(tokens), content=line,
                    ))
                  unparseable = iLine
                # if wrong number of tokens
            # if thoroughness >= 4:
          # for
        # with file
        
        # 
        # thoroughness >= 3: each file has the correct number of lines
        # 
        if nLines != nExpectedPoints:
          logging.error("File '{}' has {} lines, {} expected"
            .format(fileName, nLines, nExpectedPoints)
            )
          success = False
        # if
        if unparseable is not None: # error message has already been printed
          success = False
      # for files
    # if thoroughness >= 3
      
    
    #
    # thoroughness >= 5: ???
    # 
    if thoroughness >= 5:
      logging.warning("Chimney.verify(thoroughness=5) not implemented yet.")
    
    return success
  # verify()
  
  
  def printTimers(self, out = logging.info):
    out("""Timing of `ChimneyReader.readout()`:
      * setup:      {setup}
      * readout:    {channel} (see breakout below)
      * writing:    {writing}
      * total:      {readout}
      """.format(
        **dict([
          ( timerName, timer.toString("ms", options=('times', 'average')) )
          for timerName, timer in self.timers.items()
        ])
      )
      )
    self.scope.printTimers(out)
  # printTimers()
  
  def setupSourceSpecs(self):
    return ChimneyReader.makeSourceSpecs(self.readerState)
  
  @staticmethod
  def tempDirName(sourceInfo):
    return sourceInfo.formatString(ChimneyReader.WaveformDirectory) + "_inprogress"
  
  @staticmethod
  def resetReaderState(readerState = None, chimney = None, N = None):
    if readerState is None:
      assert chimney is not None
      assert N is not None
      readerState = ReaderState()
    if chimney is not None: readerState.chimney = chimney
    if N is not None: readerState.N = N
    readerState.cableTag = ChimneyReader.CableTags[readerState.chimney[:2].upper()]
    readerState.cableNo = ChimneyReader.MaxCable
    readerState.position = ChimneyReader.MinPosition
    return readerState
  # resetReaderState()
  
  
  @staticmethod
  def makeSourceSpecs(readerState):
    sourceInfo = drawWaveforms.WaveformSourceInfo(
      chimney=readerState.chimney, connection=readerState.cable(),
      position=readerState.position, channelIndex=1,
      index=readerState.firstIndex()
      )
    sourceInfo.updateChannel()
    sourceDir = sourceInfo.formatString(ChimneyReader.WaveformDirectory)
    return drawWaveforms.WaveformSourceFilePath(
      sourceInfo,
      filePattern=ChimneyReader.WaveformFilePattern,
      sourceDir=ChimneyReader.tempDirName(sourceInfo),
      )
  # makeSourceSpecs()
  
  @staticmethod
  def incrementReaderState(readerState, n = 1):
    if readerState.position == ChimneyReader.MaxPosition:
      readerState.position = ChimneyReader.MinPosition
      if readerState.cableNo == ChimneyReader.MinCable:
        readerState.cableNo = None
        readerState.position = None
        return False
      else: readerState.cableNo -= 1
    else: readerState.position += 1
    return (n <= 1) or ChimneyReader.incrementReaderState(readerState, n-1)
  # incrementReaderState()
  
  
# class ChimneyReader


################################################################################
### ReaderState test

if __name__ == "__main__":
  
  import argparse
  
  parser = argparse.ArgumentParser(
    description=__doc__
    )
  
  parser.add_argument("--ip", action="store", dest="IPaddress",
    help="IP address of the oscilloscope [%(default)s]", default=DefaultIP)
  parser.add_argument("--chimney", "-C", action="store",
    help="chimney to start with [%(default)s]", default="EW00")
  parser.add_argument('--fake', '-n', action='store_true',
     help="do not talk to the oscilloscope and make up the data")
  
  arguments = parser.parse_args()
  
  reader = ChimneyReader("EW00", fake=arguments.fake)
  
  print """Quick start:
  start()
  next()
  ...
  
  """
  
  LastCommand = None
  while True:
    
    try:
      print >>sys.stderr, "$ ",
      FullCommand = sys.stdin.readline().strip()
    except KeyboardInterrupt:
      print "Next time be a good kid and write `quit`."
      break
    #
    
    if not FullCommand.strip() and LastCommand:
      FullCommand = LastCommand
      print "(repeat)", FullCommand
    
    if FullCommand.strip().split(None, 1)[0].lower().startswith("quit"): break
    
    try:
      eval("reader." + FullCommand.strip())
    except Exception as e:
      logging.error(e)
    
    LastCommand = FullCommand
    
  # while True
  sys.exit(0)
  
# main

################################################################################
