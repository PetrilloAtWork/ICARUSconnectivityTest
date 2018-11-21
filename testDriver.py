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

DefaultNetwork = '192.168.230'
# DefaultIP = DefaultNetwork + '.71'
DefaultIP = DefaultNetwork + '.29'


################################################################################
### importing and default setup
import drawWaveforms
from scopeTalker import TDS3054Ctalker
import numpy
import random
import sys
import re
import os
import logging

# set verbosity level to `INFO`
logging.getLogger().setLevel(logging.INFO)

logging.info("""Default oscilloscope IP is now {DefaultIP}.
  A different default can be set by changing `{moduleName}.DefaultIP` value.
  A reader can be initialised with a different IP via constructor argument IP
  (e.g. `reader = {moduleName}.ChimneyReader(IP="192.168.230.71")`).
  """.format(DefaultIP=DefaultIP, moduleName=__name__))


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
  
  def __init__(self,
   chimney = None, IP = DefaultIP, N = 10,
   quiet = True, fake = False
   ):
    self.scope = TDS3054Ctalker(IP, connect=not fake)
    self.readerState = ReaderState()
    self.readerState.chimney = chimney
    self.readerState.N = N
    self.setQuiet(quiet)
    self.setFake(fake)
    self.canvas = None
  # __init__()
  
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
      raise RuntimeError("\"start()... which chimney??")
    if not self.readerState.isChimney(self.readerState.chimney):
      raise RuntimeError("%r is not a valid chimney." % self.readerState.chimney)
    
    self.readerState.cableTag = ChimneyReader.CableTags[self.readerState.chimney[:2].upper()]
    self.readerState.cableNo = self.MaxCable
    self.readerState.position = self.MinPosition
    
    self.sourceSpecs = self.setupSourceSpecs()
    
    # here we assume that (1) `waveformInfo` is complete enough for the
    # directory name and (2) that name is common to all the files
    tempDir = self.tempDirName(self.sourceSpecs.sourceInfo)
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
    
    for iSet in range(self.readerState.N):
      for iChannel in range(waveformInfo.MaxChannels):
        
        #
        # set the state
        #
        channelNo = iChannel + 1
        waveformInfo.setChannelIndex(channelNo)
        
        #
        # read the data from the oscilloscope
        #
        logging.debug("exec readout()")
        Time, Volt = (
          readData(waveformInfo.channelIndex)
          if not self.readerState.fake
          else (
            numpy.arange(0.0, 1.0E-5 * self.scope.WaveformSamples, 1.0E-5),
            numpy.arange(0.0, 1.0E-6 * self.scope.WaveformSamples, 1.0E-6),
          ))
        
        #
        # save it in a file
        #
        waveformFilePath = self.currentWaveformFilePath()
        self.writeWaveform(waveformFilePath, Time, Volt)
        
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
    self.plotLast()
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
  
  def setupSourceSpecs(self):
    sourceInfo = drawWaveforms.WaveformSourceInfo(
      chimney=self.readerState.chimney, connection=self.readerState.cable(),
      position=self.readerState.position, channelIndex=1,
      index=self.readerState.firstIndex()
      )
    sourceInfo.updateChannel()
    sourceDir = sourceInfo.formatString(ChimneyReader.WaveformDirectory)
    return drawWaveforms.WaveformSourceFilePath(
      sourceInfo,
      filePattern=ChimneyReader.WaveformFilePattern,
      sourceDir=self.tempDirName(sourceInfo),
      )
  # setupSourceSpecs()
  
  def tempDirName(self, sourceInfo):
    return sourceInfo.formatString(ChimneyReader.WaveformDirectory) + "_inprogress"
  
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
