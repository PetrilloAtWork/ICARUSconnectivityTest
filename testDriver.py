#!/usr/bin/env python

# from testDriver import * ; reader = ChimneyReader("EW00") ; reader.start()

__doc__ = """
Interactive driver for the scope reader.

So far, only python environment stuff is usable (see `ChimneyReader`).
"""

################################################################################
### default settings

DefaultNetwork = '192.168.230'
DefaultIP = DefaultNetwork + '.71'

################################################################################
### script customization utilities

def counterFile(): return "waveform_id_%d.txt" % IPaddress[-1]
def listFile(): return "waveform_list_%d.txt" % IPaddress[-1]

def loadScopeReader(IP):
  global IPaddress
  IPaddress = map(int, IP.split('.'))
  moduleName = "scope_readerB%d" % IPaddress[-1]
  
  global scope_reader
  try:
    del scope_reader
    del sys.modules['scope_reader']
  except: pass
  
  import importlib
  scope_reader = importlib.import_module(moduleName)
  
  print "Imported '%s' (as 'scope_reader')" % moduleName
  
  global quickAnalysis
  quickAnalysis = scope_reader.quickAnalysis
  
# loadScopeReader()


################################################################################
### importing and default setup
import drawWaveforms
import random
import sys
import re
import os

loadScopeReader(DefaultIP)
print "Use `loadScopeReader(<IP address>)` to load a different one."


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


def removeLinesFromFile(filePath, lines):
  
  tempFile = filePath + ".tmp"
  nRemoved = 0
  with open(filePath, 'r') as source, open(tempFile, 'w') as dest:
    
    for line in source:
      if line.strip() in lines:
        nRemoved += 1
        continue
      dest.write(line)
    # for
  # with
  os.remove(filePath)
  os.rename(tempFile, filePath)
  return nRemoved
# removeLinesFromFile()


################################################################################
### scope reading management utilities

def setCounter(position = 1, N = 10, quiet = False):
  
  fileName = counterFile()
  
  if not quiet:
    with open(fileName, "r") as f:
      oldValue = f.readline().strip()
  
  with open(fileName, "w") as f:
    print >>f, (N * (position - 1) + 1)
  
  if not quiet:
    with open(fileName, "r") as f:
      newValue = int(f.readline().strip())
  
  if not quiet:
    print "Counter in '%s' set from %s to %s" % (fileName, oldValue, newValue)
  
# setCounter()

def resetCounter(N = 10, quiet = False): setCounter(N=N, quiet=quiet)


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
  
# class ReaderState


################################################################################
### ChimneyReader: helper with functions for a DAQ workflow

class ChimneyReader:
  
  CableTags = { 'EE': 'V', 'EW': 'S', 'WE': 'V', 'WW': 'S', }
  
  MinPosition = 1
  MaxPosition = 8
  MinCable = 1
  MaxCable = 18
  
  def __init__(self, chimney = None, N = 10, quiet = True):
    self.readerState = ReaderState()
    self.readerState.chimney = chimney
    self.readerState.N = N
    self.setQuiet(quiet)
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
    
    self.printNext()
  # start()
  
  def command(self):
    """quickAnalysis(10, 'CHIMNEY_EW9','CONN_V01','POS_1')"""
    return "quickAnalysis(%(N)d, 'CHIMNEY_%(chimney)s', 'CONN_%(cableTag)s%(cableNo)02d', 'POS_%(position)s')" % vars(self.readerState)
  
  def printNext(self):
    if self.readerState.chimney is None:
      print "You'd better set a chimney first."
      return False
    if self.readerState.cableNo is None or self.readerState.position is None:
      print "No test next."
      return False
    print "next(): %s => %s" % (self.readerState.stateStr(), self.command())
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
    self.setCounter()
    print "exec %s" % self.command()
    if not self.readerState.fake: exec self.command()
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
    
    # removal code will go here:
    # 1) remove data files
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
    
    # 2) remove entries in the data list
    nRemoved = removeLinesFromFile(listFile(), map(os.path.basename, dataFiles))
    print "Removed %d/%d lines from '%s'" % (nRemoved, len(dataFiles), listFile())
    
    # 3) reset counter (not needed since it's manually set each time)
    self.setCounter()
    
    if (n > 1) and not self.removeLast(n-1): return False
    if n == 1: self.printNext()
    return True
  # removeLast()
  
  def setupSourceSpecs(self):
    sourceSpecs = drawWaveforms.WaveformSourceParser()
    sourceSpecs.setup(
      self.readerState.chimney, self.readerState.cable(),
      self.readerState.position, 1, # channelIndex
      self.readerState.firstIndex(),
      filePattern="waveform_CH%(channelIndex)d_CHIMNEY_%(chimney)s_CONN_%(connection)s_POS_%(position)d_%(index)d.csv",
      sourceDir = scope_reader.folder_name
      )
    return sourceSpecs
  # setupSourceSpecs()
  
  def setCounter(self):
    setCounter(position=self.readerState.position, N=self.readerState.N, quiet=self.readerState.quiet)

# class ChimneyReader


################################################################################
### ReaderState test

if __name__ == "__main__":
  
  readerState = ReaderState()
  
  while True:
    
    try:
      FullCommand = sys.stdin.readline().strip()
    except KeyboardInterrupt:
      print "Next time be a good kid and write `quit`."
      break
    #
    
    Command, Arguments = FullCommand.split(1)
    Arguments = Arguments.split()
    command = Command.lower()
    
    if command == 'quit':
      print "Exiting."
      break
    elif command in ( 'enable', 'disable', ):
      getattr(readerState, command)()
      continue
    elif command in [ 'chimney', 'ch', 'c' ]:
      if len(Arguments) == 0:
        print "WHICH chimney?"
        continue
      chimney = Arguments[0]
      readerState.startChimney(chimney)
    else:
      readerState.execute(command)
    
    
  # while True
  sys.exit(0)
  
# main

################################################################################
