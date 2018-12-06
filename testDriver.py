#!/usr/bin/env python

#
# from testDriver import ChimneyReader ; reader = ChimneyReader("config/FlangeChimneyTest_scope1.ini"); reader.resume("A0")
# reader.next()
#

__doc__ = """
Interactive driver for the scope reader.

So far, only python environment stuff is usable interactively
(see `ChimneyReader`), but running from python is still quite better.
"""

__version__ = "5.2"

# TODO:
# * `ChimneyReader.start()` warn if the chimney has already been completed
# * create a wrapper python script dropping to interactive

################################################################################
### default settings


################################################################################
### importing and default setup
import drawWaveforms
from stopwatch import StopWatch, WatchCollection
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


def getCaseUnsensitive(d, key, *default):
  assert(len(default) <= 1)
  key = key.lower()
  for k, v in d.items():
    if key == k.lower(): return v
  if len(default) > 0: return default[0]
  raise KeyError(key)
# getCaseUnsensitive()


def flatten(l):
  fl = []
  for item in l: fl.extend(item)
  return fl
# flatten()

class ANSIClass:
  
  Black   = 0
  Red     = 1
  Green   = 2
  Blue    = 4
  Yellow  = Red + Green
  Cyan    = Blue + Green
  Magenta = Red + Blue
  White   = Red + Green + Blue
  
  def __init__(self, colors = True):
    self.colors = colors
  
  def enableColor(self, enable = True): self.colors = enable
  
  def fgColor(self, color, highlight = False):
    return self._activate(ANSIClass.composeColor(
      ANSIClass.highlight() if highlight else None, ANSIClass.fgCode(color),
      ))
  # fgColor()
  
  def red(self, highlight = False):
    return self.fgColor(ANSIClass.Red, highlight=highlight)
  def green(self, highlight = False):
    return self.fgColor(ANSIClass.Green, highlight=highlight)
  def blue(self, highlight = False):
    return self.fgColor(ANSIClass.Blue, highlight=highlight)
  def yellow(self, highlight = True):
    return self.fgColor(ANSIClass.Yellow, highlight=highlight)
  def magenta(self, highlight = False):
    return self.fgColor(ANSIClass.Magenta, highlight=highlight)
  def cyan(self, highlight = False):
    return self.fgColor(ANSIClass.Cyan, highlight=highlight)
  def white(self, highlight = True):
    return self.fgColor(ANSIClass.White, highlight=highlight)
  def black(self, highlight = False):
    return self.fgColor(ANSIClass.Black, highlight=highlight)
  def gray(self, highlight = False): return self.white(highlight=highlight)
  
  def _activate(self, code): return code if self.colors else ""
  
  @staticmethod
  def fgCode(color): return str(30 + color)
  
  @staticmethod
  def reset(): return ANSIClass.composeColor("0")
  
  @staticmethod
  def highlight(): return "1"
  
  @staticmethod
  def composeColor(*codes):
    return ANSIClass.escapeCode(';'.join(filter(None, codes)) + 'm')
  
  @staticmethod
  def escapeCode(code): return "\x1B[" + code
  
# class ANSIClass
ANSI = ANSIClass()


################################################################################
### Reader state: describes what we are doing right now (incomplete)

class ReaderState:
  
  ChimneyMatcher = re.compile('([EW]{2}|[A-D,F])([0-9]{1,2})')
  CableMatcher = re.compile('[A-Z][0-9]{2}')
  
  def __init__(self, chimney = None, N = 10, ):
    self.enabled = False
    self.confirm = True
    self.test = ""
    self.cableTag = None
    self.cableNo = None
    self.position = None
    self.N = N
    
    self.setChimney(chimney)
    
    self.quiet = False
    self.fake = False
  # __init__()
  
  def enable(self):
    print "All commands are now going to be executed for real."
    self.enabled = True
  def disable(self):
    print "All commands are now just being printed and NOT going to be executed."
    self.enabled = False
  
  def hasChimney(self): return self.chimney is not None
  
  def setChimney(self, chimney):
    if chimney is None:
      self.chimney = None
      self.chimneySeries = None
      self.chimneyNumber = 0
      return
    info = ReaderState.splitChimney(chimney.upper())
    if info is None:
      raise RuntimeError("ReaderState.setChimney('{}'): invalid chimney."
                         .format(chimney))
    self.chimneySeries, self.chimneyNumber = info
    self.chimney \
      = ReaderState.formatChimney(self.chimneySeries, self.chimneyNumber)
    self.cableTag = ChimneyReader.CableTags[self.chimneySeries]
  # setChimney()
  
  @staticmethod
  def splitChimney(chimney):
    info = ReaderState.ChimneyMatcher.match(chimney.upper())
    chimneyNumber = info.group(2).lstrip('0')
    return ( info.group(1), int(chimneyNumber) if chimneyNumber else 0, ) \
      if info is not None else None
  # splitChimney()
  
  @staticmethod
  def formatChimney(series, n): return "{}{:02d}".format(series, n)
  
  @staticmethod
  def isChimney(chimney):
    return ReaderState.splitChimney(chimney.upper()) is not None
  
  @staticmethod
  def isCable(cable):
    return ReaderState.CableMatcher.match(cable.upper()) is not None
  
  def cable(self): return "%(cableTag)s%(cableNo)02d" % vars(self)
  
  def firstIndex(self):
    return drawWaveforms.WaveformSourceInfo.firstIndexOf(self.position, self.N)
  
  def stateStr(self):
    return "Test %(test)s chimney %(chimney)s connection %(cableTag)s%(cableNo)02d position %(position)d" % vars(self)
  
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
  
  def makeWaveformSourceInfo(self,
   channelNo = None, index = None, testName = None,
   ):
    return drawWaveforms.WaveformSourceInfo(
      chimney=self.chimney, connection=self.cable(), channelIndex=channelNo,
      position=self.position, index=index,
      testName=(testName if testName is not None else self.test),
      )
  # makeWaveformSourceInfo()
  
  
  def updateWaveformSourceInfo(self, sourceInfo):
    """Updates a `WaveformSourceInfo` after `ReaderState` has moved to a
    different position."""
    sourceInfo.connection = self.cable()
    sourceInfo.setPosition(self.position)
    sourceInfo.test = self.test
  # updateWaveformSourceInfo()

  
# class ReaderState


class ReaderStateSequence:
  """Defines a sequence of states for the complete test.
  
  The sequence defined by `goNext()`, `goPrev()` and `reset()` is to
   * go through the sequence of all positions for each test
   * go through the sequence of all tests for each cable
   * go through all cables in the chimney
  
  The list of positions is 1 to 8, while the list of cables is descending,
  18 to 1. The list of test is directly adopted from the constructor parameter.
  
  Other implementations can derive from this one and redefine the sequence
  and the ranges.
  """
  
  def __init__(self, state,
   tests = [ '' ],
   cables = range(18, 0, -1),
   positions = range(1, 9),
   ):
    self.readerState = state
    self.setPositions(positions)
    self.setTests(tests)
    self.setCables(cables)
    self.reset()
  # __init__()
  
  def reset(self):
    self.iPosition = 0
    self.iCable = 0
    self.iTest = 0
    self.updateState()
    assert self.isValid()
    assert self.isAtStart()
  # reset()
  
  def setCables(self, cables):
    assert cables
    self.cables = cables[:]
  # setCables()
  
  def setTests(self, tests):
    assert tests
    self.tests = tests[:]
  # setTests()
  
  def setPositions(self, positions):
    assert positions
    self.positions = positions[:]
  # setPositions()
  
  def state(self): return self.readerState
  
  def position(self): return self.positions[self.iPosition]
  def firstPosition(self): return self.positions[0]
  def lastPosition(self): return self.positions[-1]
  def isPosition(self):
    return (self.iPosition >= 0) and (self.iPosition < self.nPositions())
  def isFirstPosition(self): return self.iPosition == 0
  def isLastPosition(self): return self.iPosition >= (self.nPositions() - 1)
  def nPositions(self): return len(self.positions)
 
  def cable(self): return self.cables[self.iCable]
  def firstCable(self): return self.cables[0]
  def lastCable(self): return self.cables[-1]
  def isCable(self):
    return (self.iCable >= 0) and (self.iCable < self.nCables())
  def isFirstCable(self): return self.iCable == 0
  def isLastCable(self): return self.iCable >= (self.nCables() - 1)
  def nCables(self): return len(self.cables)

  def test(self): return self.tests[self.iTest]
  def firstTest(self): return self.tests[0]
  def lastTest(self): return self.tests[-1]
  def isTest(self): return (self.iTest >= 0) and (self.iTest < self.nTests())
  def isFirstTest(self): return self.iTest == 0
  def isLastTest(self): return self.iTest >= (self.nTests() - 1)
  def nTests(self): return len(self.tests)
  
  def __iter__(self): return ReaderStateSequence.Iterator(self, reset=True)
  def __len__(self): return self.nPositions() * self.nTests() * self.nCables()
  
  def setPosition(self, position):
    if self.positions.count(position) > 1:
      raise RuntimeError(
       "Can't set position {} since it's present in the sequence {} times."
       .format(position, self.positions.count(position))
       )
    # if too many position
    try: self.iPosition = self.positions.index(position)
    except ValueError:
      raise RuntimeError("{} is not a valid position to set.".format(position))
    self.updateState()
  # setPosition()
  
  def setCable(self, cableNo, resetTest = False, resetPosition = False):
    if self.cables.count(cableNo) > 1:
      raise RuntimeError(
       "Can't set cable {} since it's present in the sequence {} times."
       .format(cableNo, self.cables.count(cableNo))
       )
    # if too many cable
    try: self.iCable = self.cables.index(cableNo)
    except ValueError:
      raise RuntimeError("{} is not a valid cable to set.".format(cableNo))
    if resetTest: self.iTest = 0
    if resetPosition: self.iPosition = 0
    self.updateState()
  # setCable()
  
  def setTest(self, test, resetPosition = False):
    count = 0
    for iTest, testName in enumerate(self.tests):
      if testName.lower() != test.lower(): continue
      count += 1
      pos = iTest
    # for
    if count > 1:
      raise RuntimeError(
       "Can't set test {} since it's present in the sequence {} times."
       .format(test, count)
       )
    # if too many test
    if count == 0:
      raise RuntimeError("{} is not a valid test to set.".format(test))
    self.iTest = pos
    if resetPosition: self.iPosition = 0
    self.updateState()
  # setTest()
  
  
  def isValid(self):
    return self.isCable() and self.isTest() and self.isPosition()
  def isAtStart(self):
    return (self.iPosition == 0) and (self.iTest == 0) and (self.iCable <= 0)
  def isAtEnd(self): return self.iCable >= self.nCables()
  
  def hint(self):
    """Return a hint of what to do to prepare for the next step
    (which is the current state)."""
    return None
  # hint()
  
  def goNext(self, n = 1):
    self.iPosition += 1
    if not self.isPosition():
      self.iPosition = 0
      self.iTest += 1
    if not self.isTest():
      self.iTest = 0
      self.iCable += 1
    if not self.isCable():
      self.iPosition = 0
      self.iTest = 0
      self.iCable = self.nCables()
    if (n > 1) and not self.goNext(n-1): return False
    self.updateState()
    return self.isCable()
  # goNext()
  
  def goPrev(self, n = 1):
    self.iPosition -= 1
    if not self.isPosition():
      self.iPosition = self.nPositions() - 1
      self.iTest -= 1
    if not self.isTest():
      self.iTest = self.nTests() - 1
      self.iCable -= 1
    if not self.isCable():
      self.iPosition = self.nPositions() - 1
      self.iTest = self.nTests() - 1
      self.iCable = -1
    if (n > 1) and not self.goPrev(n-1): return False
    self.updateState()
    return self.isCable()
  # goPrev()
  
  def updateState(self):
    self.readerState.position = self.position()
    self.readerState.test = self.test()
    self.readerState.cableNo = self.cable() if self.isCable() else None
    return True
  # updateState()
  
  def stateStr(self): return self.readerState.stateStr()
  
  def __str__(self):
    return "Connection {cable} (#{iCable}) test {test} (#{iTest})" \
     " position {position} (#{iPosition})".format(
      cable=self.cable(), iCable=self.iCable,
      test=self.test(), iTest=self.iTest,
      position=self.position(), iPosition=self.iPosition,
      )
  # __str__()
  
  
  class Iterator:
    def __init__(self, stateSeq, reset = True):
      self.reset = reset
      self.stateSeq = stateSeq
    def __iter__(self): return self
    def next(self):
      if not self.stateSeq.isValid(): self.reset = True # this is for autoreset
      if self.reset:
        self.reset = False
        self.stateSeq.reset()
        return self.stateSeq
      elif not self.stateSeq.goNext():
        self.reset = True
        raise StopIteration
      return self.stateSeq
    # next()
  # class Iterator
  
# class ReaderStateSequence


class HVandPulseSequence(ReaderStateSequence):
  def __init__(self, state,
   tests = [ '' ],
   cables = flatten(zip(range(1, 10), range(10, 19))),
   positions = range(1, 9),
   ):
    ReaderStateSequence.__init__(self,
     state,
     tests=tests, cables=cables, positions=positions,
     )
  # __init__()
  
  def slot(self): return 1 + (self.cable() - 1) % 9
  
  def isLeft(self):
    return (self.cable() >= 1) and (self.cable() <= 9)
  def isRight(self):
    return (self.cable() >= 10) and (self.cable() <= 18)
  def isHV(self):
    return self.test().upper() == "HV"
  def isPulse(self):
    return self.test().lower() == "pulse"
  
  LeftColor = ANSI.red(highlight=True)
  RightColor = ANSI.yellow(highlight=False)
  PositionColor = ANSI.white()
  SlotColor = ANSI.green(highlight=True)
  
  @staticmethod
  def colorLeft(s): return HVandPulseSequence.LeftColor + s + ANSI.reset()
  @staticmethod
  def colorRight(s): return HVandPulseSequence.RightColor + s + ANSI.reset()
  @staticmethod
  def colorPosition(p):
    return HVandPulseSequence.PositionColor + str(p) + ANSI.reset()
  
  
  def sideColor(self):
    if self.isLeft():
      return HVandPulseSequence.LeftColor
    elif self.isRight():
      return HVandPulseSequence.RightColor
    else:
      return ""
  # sideColor()
  
  def sideName(self):
    if self.isLeft():
      return "left"
    elif self.isRight():
      return "right"
    else:
      return "unknown side"
  # sideName()
  
  def stateStr(self):
    
    # coloring
    chimney = self.readerState.chimney # no color
    
    cable \
      = "{tag}{no:02d}".format(tag=self.readerState.cableTag, no=self.cable())
    
    if self.isLeft():
      cable = self.colorLeft(cable)
    elif self.isRight():
      cable = self.colorRight(cable)
    
    if self.isPulse():
      test = (
        "p"
        + ANSI.white() + "u"
        + ANSI.green() + "l"
        + ANSI.black(highlight=True) + "s"
        + ANSI.red(highlight=True) + "e"
        + ANSI.reset()
       )
    elif self.isHV():
      test = ANSI.cyan() + self.test() + ANSI.reset()
    else:
      test = self.test()
    
    position = self.colorPosition(self.position())
    
    return (
      "Test {test} chimney {chimney} connection {cable} position {position}"
      .format(
        test=test,
        chimney=chimney,
        cable=cable,
        position=position,
        )
      )
    
  # stateStr()
  
  def hint(self):
    
    if self.isAtEnd():
      return "The test sequence of chimney {} is complete." \
        .format(self.readerState.chimney)
    
    # in the middle of the position sequence...
    if not self.isFirstPosition():
      return "* just turn to {posCol}position {pos}{reset}".format(
        posCol=self.PositionColor,
        reset=ANSI.reset(),
        pos=self.position(),
        )
    # if position
    
    # if changing between left and right (first position of first test)
    msg = []
    if self.isLeft(): # new slot (right to left)
      msg.append(
        "* remove pulser and ribbon cables and switch the board to {slotCol}slot {slot}{reset}"
        .format(
          slotCol=self.SlotColor, reset=ANSI.reset(),
          slot=self.slot(),
        ))
    if self.isHV():
      msg.append("* direct test box pulser output to the {sideCol}{side} HV input{reset}"
        .format(
          sideCol=self.sideColor(),
          side=self.sideName(),
          reset=ANSI.reset(),
        ))
    elif self.isPulse():
      msg.append(
        "* direct test box pulser output to the {sideCol}pulse input for {cable}{reset}"
        .format(
          sideCol=self.sideColor(),
          cable=self.readerState.cable(),
          reset=ANSI.reset(),
        ))
      if self.cable() in [ 1, 10, ]:
        msg.append("  => {white}test all the different pulse inputs to find the best one{reset}"
          .format(
            white=ANSI.white(),
            reset=ANSI.reset(),
          ))
      elif self.cable() in [ 2, 9, 11, 18, ]:
        msg.append("* {white}you may need to test different pulse inputs to find the best one{reset}"
          .format(
            white=ANSI.white(),
            reset=ANSI.reset(),
          ))
    # if pulse
    msg.extend([
      "* plug the {sideCol}{side} signal ribbon{reset} into the test box".format(
        sideCol=self.sideColor(),
        side=self.sideName(),
        reset=ANSI.reset(),
        ),
      "* turn to {posCol}position {pos}{reset}".format(
        posCol=self.PositionColor,
        reset=ANSI.reset(),
        pos=self.position(),
        ),
      ])
    # if ... else
    return "\n".join(filter(None, msg)) if msg else None
  # hint()
  
# class HVandPulseSequence



################################################################################
### ChimneyReader: helper with functions for a DAQ workflow

class ChimneyReader:
  """
  
  `ChimneyReader` now controls the communication with the oscilloscope, via a
  `ScopeTalker` object (in fact, a `TDS3054Ctalker` object).
  
  
  """
  CableTags = {
    'EE': 'V', 'EW': 'S', 'WE': 'V', 'WW': 'S', # September 2018 nomenclature
    'A':  'V', 'B':  'S', 'C':  'V', 'D':  'S', # December 2018 nomenclature
    'F':  'V',                                  # December 2018, flange only
    }
  
  MinPosition = 1
  MaxPosition = 8
  MinCable = 1
  MaxCable = 18
  
  TestSets = {
    'HV':     {
      'tests': [ 'HV', ],
      'sequence': HVandPulseSequence,
      },
    'Pulse':  {
      'tests': [ '', ],
      },
    'Flange': {
      'tests': [ 'PULSE', 'HV', ],
      'sequence': HVandPulseSequence,
      },
  } # TestSets
  
  WaveformFilePattern = drawWaveforms.WaveformSourceFilePath.StandardPattern
  WaveformDirectory = drawWaveforms.WaveformSourceFilePath.StandardDirectory
  
  DefaultVerificationThoroughness = 4 # see `verify()`
  
  TimerPlotNamespace = 'plot'
  
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
    
    self.scope = TDS3054Ctalker(params.IP, connect=not params.fake)
    self.selectTestSuite(params.testSuite, chimney=chimney, N=params.N)
    
    ANSI.enableColor(params.useColors)
    self.nextHints = params.printHints
    self.setQuiet(True) # this will be one day removed
    self.setFake(params.fake)
    self.storageParams = params.storage
    self.drawWaveforms = drawWaveforms.useRenderer(params.drawWaveforms)
    self.drawOptions = params.draw
    self.canvas = None
    self.timers = WatchCollection(
      'setup'        ,
      'channel'      ,
      'writing'      ,
      { 'name': 'readout', 'comment': '(breakout below)', },
      { 'name': 'graphicUpdate', 'description': 'update display', 'namespace': ChimneyReader.TimerPlotNamespace, },
      title="Timing of `ChimneyReader.readout()`",
      ) # timers
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
    
    #
    # This system is not as smart as I was hoping...
    # I need to parse all configuration files one by one to detect all the
    # included files, but the included files should be overridden by the
    # includers. Therefore eventually I have to load them in reverse order.
    #
    try:
      from configparser import SafeConfigParser, NoSectionError, NoOptionError
    except ImportError:
      from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError
    configFile = SafeConfigParser()
    getConfig = OptionDefault(configFile)
    if isinstance(configurationFilePath, (str, unicode, )):
      configurationFilePath = [ configurationFilePath, ]
    readConfigurations = []
    while configurationFilePath:
      fileName = configurationFilePath[0]
      configFile.readfp(open(fileName, 'r'), fileName)
      logging.debug("Queued configuration file: '{}'".format(fileName))
      readConfigurations.append(fileName)
      del configurationFilePath[0]
      # [Include] section
      configDir = os.path.split(fileName)[0]
      try: inclSection = configFile.items("Include")
      except NoSectionError: inclSection = []
      configFile.remove_section("Include")
      for _, includeList in inclSection:
        for includeFile in includeList.split():
          if not os.path.isabs(includeFile):
            includeFile = os.path.join(configDir, includeFile)
          if includeFile in readConfigurations: continue
          configurationFilePath.append(includeFile)
        # for include files
      # for include lines
    # while
    
    # now reread them in the right order:
    configFile = SafeConfigParser()
    getConfig = OptionDefault(configFile)
    for fileName in reversed(readConfigurations):
      configFile.readfp(open(fileName, 'r'), fileName)
      configFile.remove_section("Include")
      logging.info("Configuration file: '{}'".format(fileName))
    # for
    
    
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
    # Colors: whether to use colors on the console output (ANSI/VT100).
    # Default is ON.
    #
    localParams.useColors = getConfig.bool('Colors', True)
    
    #
    # Hints: whether to print hints on how to prepare for the next data taking.
    # Default is ON.
    #
    localParams.printHints = getConfig.bool('Hints', True)
    
    #
    # TestSuite: name of the test being performed (see `ChimneyReader.TestSets`)
    # Default is `pulse`.
    localParams.testSuite = getConfig('TestSuite', "Pulse")
    
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
    try:
      localParams.drawWaveforms \
        = "ROOT" if getConfig.bool('DrawWaveforms', True) else None
    except ValueError:
      localParams.drawWaveforms = getConfig('DrawWaveforms')
    # try ... except
    
    #
    # Drawing options:
    # 
    # PlotGrid: how to arrange the plots in the canvas; valid values are defined
    #           in `drawWaveforms.VirtualRenderer.makeWaveformCanvas()` and
    #           include: 'horizontal', 'vertical' and 'square' (also 'default')
    # Default: 'default'          
    #
    localParams.draw = {}
    localParams.draw['grid'] = getConfig('PlotGrid', 'default')
    
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
  # _configure()
  
  
  def selectTestSuite(self, name, chimney = None, N = None):
    try: self.testSpecs = getCaseUnsensitive(ChimneyReader.TestSets, name)
    except KeyError:
      raise RunetimeError(
        "Unknown test suite: '{}'\nValid test suites: {})".format(
          name, "', '".join(ChimneyReader.TestSets),
          )
        )
    self.testSuiteName = name
    # try ... except
    try:
      if not chimney: chimney = self.readerState.state().chimney
      if N is None: N = self.readerState.state().N
    except AttributeError: pass
    
    SeqClass = self.testSpecs.get('sequence', ReaderStateSequence)
    self.readerState = SeqClass \
      (ReaderState(chimney=chimney, N=N), tests=self.testSpecs['tests'])
  # selectTestSuite()
  
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
  
  def setQuiet(self, quiet = True): self.readerState.state().quiet = quiet
  def setFake(self, fake = True): self.readerState.state().fake = fake
  
  def start(self, chimney = None, N = None):
    tempDir = self._start(chimney=chimney, N=N)
    logging.info \
      ("Output for this chimney will be written into: '{}'".format(tempDir))
    self.printNext()
  # start()
  
  def resume(self, chimney = None, N = None, outputDir = None):
    tempDir = self._start(chimney=chimney, N=N)
    if not outputDir: outputDir = tempDir
    logging.info \
      ("Looking for data already acquired in: '{}'".format(tempDir))
    
    for iSkip, files in \
     enumerate(self.expectedFilesPerPosition(sourceDir=outputDir)):
      for fileName in files:
        if not os.path.isfile(fileName):
          logging.debug("Missing output file: '{}' (skip {})".format(
            fileName, iSkip + 1,
            ))
          break # missing file
      else:
        self.skipToNext()
        continue
      break
    else: iSkip += 1
    logging.info("Found data for {} positions.".format(iSkip))
    self.printNext()
  # resume()
  
  def readout(self):
    # We try to avoid code duplication: since some code putting together file
    # names already exists in `drawWaveforms`, we use code from there.
    # The file name composing code relies on a "state" which is a superset of
    # when is included in `ReaderState` (except for `N`): we use that state
    # (`WaveformSourceInfo` object) to track the state internally.
    # Note that here the state that is also in `readerState` is not changed.
    
    
    waveformInfo = self.readerState.state().makeWaveformSourceInfo()
    waveformInfo.setFirstIndex(N=self.readerState.state().N)
    self.sourceSpecs.setSourceInfo(waveformInfo)
    
    with self.timers['readout'], self.timers['setup']:
      if not self.readerState.state().fake: self.scope.readDataSetup()
    
    for iSet in range(self.readerState.state().N):
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
              if not self.readerState.state().fake
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
    if not self.readerState.state().hasChimney():
      logging.error("You'd better set a chimney first.")
      return False
    if self.readerState.isAtEnd():
      logging.info("Chimney sequence is complete: time to `verify()` that everything is in place.")
      return False
    logging.info("next(): {}".format(self.readerState.stateStr()))
    if self.nextHints:
      hint = self.readerState.hint()
      if hint: logging.info("Hint:\n{}".format(hint))
    return True
  # printNext()
  
  def skipToNext(self, n = 1):
    if not self.readerState.goNext(n=n): return False
    self._updateSourceInfo()
    return True
  # skipToNext()
  
  def skipToPrev(self, n = 1):
    if not self.readerState.goPrev(n=n): return False
    self._updateSourceInfo()
    return True
  # skipToPrev()
  
  def jumpTo(self, cable = None, position = 1, test = None):
    if cable is not None:
      self.readerState.setCable(cable, resetTest=False, resetPosition=True)
    if test is not None: self.readerState.setTest(test, resetPosition=True)
    if position is not None: self.readerState.setPosition(position)
    self.readerState.state().updateWaveformSourceInfo(self.sourceSpecs.sourceInfo)
    self.printNext()
  # jumpTo()
  
  def readNext(self):
    self.readout()
    if self.drawWaveforms: self.plotLast()
    self.skipToNext()
    return self.printNext()
  # readNext()
  next = readNext
  
  def listLast(self):
    return self.sourceSpecs.allPositionSources(N=self.readerState.state().N)
  
  def plotLast(self):
    # this will work only if `drawWaveforms` module is loaded
    
    with self.timers.withNamespace("plot"):
      self.canvas = drawWaveforms.plotAllPositionWaveforms(
        self.sourceSpecs,
        canvas=self.canvas,
        options={ 'timers': self.timers, 'grid': self.drawOptions['grid'], },
        )
      with self.timers['graphicUpdate']:
        self.canvas.Update()
    # with plot namespace
  # plotLast()
  
  def removeLast(self, n = 1, confirmMode = 1):
    if not self.skipToPrev():
      print >>sys.sdterr, "There was no previous reading! now you did it."
      return False
    
    # remove data files
    dataFiles = self.listLast()
    if isinstance(confirmMode, int):
      askConfirm = confirmMode > 0
      nextConfirmMode = max(confirmMode - 1, 0)
    else:
      askConfirm = confirmMode
      nextConfirmMode = confirmMode
    # confirmMode
    if askConfirm:
      if not confirm("Remove %d files from %s?" % (len(dataFiles), self.readerState.state().stateStr())):
        print "You're the boss."
        self.skipToNext()
        self.printNext()
        return False
    else: # print what we are doing
      logging.info("Removing {nFiles} files from {state}".format
        (nFiles=len(dataFiles), state=self.readerState.state().stateStr()))
    # if ... else
    for path in dataFiles:
      if not os.path.exists(path):
        print >>sys.stderr, "Expected data file '%s' not found." % path
        continue
      try: os.remove(path)
      except IOError, e:
        print >>sys.stderr, "Failed to remove '%s': %s" % (filePath, e)
    # for
    
    if (n > 1) and not self.removeLast(n-1, confirmMode=nextConfirmMode):
      return False
    if n == 1: self.printNext()
    return True
  # removeLast()
  
  
  def checkOutput \
   (self, outputDir, thoroughness = DefaultVerificationThoroughness):
    """Scans the output directory finding if data files are missing or spurious.
    
    Only CSV files (ending in '.csv') are considered.
    The verification is attempted on the temporary output directory.
    
    Thoroughness level:
    - 0: check that the number of CSV files in the output directory is the right
         one (5760)
    - 1: check that there are no missing files
    - 2: check that there are no spurious files
    - 3: check that all the files have the expected number of lines each
    - 4: check that all the files are fully parseable
    """
    
    #
    # expected files
    #
    expectedFiles = set(self.expectedFiles(sourceDir=outputDir))
    
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
      if len(CSVfiles) == len(expectedFiles):
        logging.debug("Found the expected number ({}) of CSV files found in '{}'.".format(len(CSVfiles), outputDir))
        return True
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
      else:
        logging.debug("All {} expected CSV files found in '{}'.".format(len(expectedFiles), outputDir))
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
      else:
        logging.debug("No spurious CSV files found in '{}'.".format(outputDir))
      # if missing
    # if thoroughness >= 2
    
    dataFiles = CSVfiles & expectedFiles
    
    # 
    # thoroughness >= 3
    # 
    if thoroughness >= 3:
      watch = StopWatch()
      nExpectedPoints = self.scope.WaveformSamples
      for iFile, fileName in enumerate(sorted(dataFiles)):
        logging.info \
          ("[{}/{}] Checking: '{}'".format(iFile + 1, len(dataFiles), fileName))
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
      else: iFile += 1 # for files
      logging.info("{} files checked in {}.".format(iFile, watch.toString()))
    # if thoroughness >= 3
    
    #
    # thoroughness >= 5: ???
    # 
    if thoroughness >= 5:
      logging.warning("Chimney.verify(thoroughness=5) not implemented yet.")
    
    return success
  # checkOutput()
  
  
  def verify(self,
   outputDir = None,
   thoroughness = DefaultVerificationThoroughness,
   finalize = True,
   ):
    """Scans the output directory finding if data files are missing or spurious.
    
    The verification is attempted on the temporary output directory; if the
    verification succeeds and `finalize` is not `False`, the output directory
    is then renamed from temporary to output directory.
    If that is not found, the final output directory is tried instead, and no
    renaming takes place in any case.
    Also if the `outputDir` is explicitly specified, it is not going to be
    renamed in any case.
    
    For thoroughness level explanation, see `checkOutput()`.
    """
    
    if not self.readerState.state().hasChimney():
      logging.error("No chimney being parsed.")
      return False
    
    # sanity check on renaming before the potentially long check happens
    outputDir, finalOutDir = ChimneyReader.finalOutputDirectoryTarget \
      (self.sourceSpecs.sourceInfo, outputDir=outputDir)
    
    if finalize and (finalOutDir is not None) and os.path.exists(finalOutDir):
      raise RuntimeError("Final output directory '{}' already exists."
        " Either remove it (recommended), or disable output finalization"
        " (`verify(finalize=False)`)".format(finalOutDir))
    # if finalize sanity check
    
    verified = self.checkOutput(outputDir, thoroughness=thoroughness)
    
    if not verified:
      logging.error("Verification failed: please correct the problems before proceeding to archive.")
      return False
    #
    
    if finalize:
      logging.debug("Verification successful: proceeding with finalization.")
      outputDir = self._finalize(outputDir, finalOutDir)
    # if finalizing
    
    logging.info("Output is now in directory '{}'.".format(outputDir))
    logging.info("Verification was successful: now generate a script for archiving with `generateArchivalScript()`.")
    
    return True
  # verify()
  
  
  def infoFilePath(self, scriptDir = None):
    
    if scriptDir is None:
      scriptDir = ChimneyReader.outputDirName(self.sourceSpecs.sourceInfo)
    
    infoFileName = "INFO-{}.txt".format(os.path.basename(scriptDir))
    
    return os.path.join(scriptDir, infoFileName)
    
  # infoFilePath()
  
  
  def generateInfoFile(self, scriptDir = None):
    
    import time
    
    infoFilePath = self.infoFilePath(scriptDir=scriptDir)
    logging.info("INFO file: '{}'".format(infoFilePath))
    
    with open(infoFilePath, 'w') as f:
      print >>f, """{softwareName} version {softwareVersion}
---------------------------------------
Chimney:      {chimney}
Date:         {date}
Oscilloscope: {scopeName}
  IP:         {scopeAddress}
From host:    {hostname}
     user:    {username}""".format(
      softwareName=__name__,
      softwareVersion=__version__,
      chimney=self.sourceSpecs.sourceInfo.chimney,
      date=time.ctime(),
      scopeName=("(fake)" if self.readerState.state().fake 
                 else self.scope.description
                 ),
      scopeAddress=self.scope.address,
      hostname=ChimneyReader.getHostName(),
      hostIP=ChimneyReader.getHostIP(),
      username=ChimneyReader.getUserName(),
      )
    return infoFilePath
  # generateInfoFile()
  
  
  def generateArchivalScript(self, scriptDir = None, sourceDir = None):
    """Creates a script to be run to transfer all data.
    
    Run `verify()` first!
    If `verified` is set to `False`, a script will be generated to transfer the
    unverified files. Please fix the files instead!
    """
    
    if not self.readerState.state().hasChimney():
      logging.error("No chimney being parsed.")
      return False
    
    if sourceDir is None:
      sourceDir = ChimneyReader.outputDirName(self.sourceSpecs.sourceInfo)
      if not os.path.isdir(sourceDir):
        logging.error(
          "Cowardly refusing to write a transfer script for a directory that does not exist yet ('{}')."
          .format(sourceDir)
          )
        return None
    # if
    
    if scriptDir is None: scriptDir = sourceDir
    scriptName = "archive_{}.sh".format(os.path.basename(sourceDir))
    scriptPath = os.path.join(scriptDir, scriptName)
    logging.info("Archive script: '{}'".format(scriptPath))
    
    #
    # collect the expected files
    #
    expectedFiles = self.expectedFiles(sourceDir=sourceDir)
    
    #
    # write the script
    #
    infoFilePath = self.infoFilePath(scriptDir=scriptDir)
    ScriptHeader = """#!/usr/bin/env bash
#
# Script to archive all validated CSV data files.
# It can be rested ("dry run") by setting the environment variable `FAKE` to non-zero value.
#

[[ -n "${{FAKE//0}}" ]] || unset FAKE

#
# remote server settings
#
declare -r DestServer="{DestServer}"
declare -r DestDir="{DestDir}"
declare -r User="{User}"

#
# source settings
#
declare -r SourceBaseDir="{SourceBaseDir}"

#
# copy!
#
rsync ${{FAKE:+'-n'}} -avz --chmod='ug+rw' --progress --files-from='-' "$SourceBaseDir" "${{User:+"${{User}}@"}}${{DestServer}}:${{DestDir:+"${{DestDir}}/"}}" <<EOL
{infoFile}""".format(
      DestServer=self.storageParams.server,
      DestDir=self.storageParams.outputDir,
      User=self.storageParams.user,
      SourceBaseDir=os.path.dirname(os.path.abspath(sourceDir)),
      infoFile=infoFilePath,
      )
    ScriptFooter = """EOL
"""
    with open(scriptPath, 'w') as f:
      print >>f, ScriptHeader
      for sourceFile in expectedFiles:
        print >>f, sourceFile
      print >>f, ScriptFooter
    # with
    import stat
    os.chmod(scriptPath, stat.S_IRWXU | stat.S_IXGRP | stat.S_IXOTH | stat.S_IRGRP | stat.S_IROTH)
    
    logging.info("""The archival script '{scriptName}' has been generated.
      Now that script can be run on a new shell, and the work on this chimney ({chimney}) is complete.
      You can exit the python shell, or start a new chimney with `start()`.
      """.format(
        scriptName=scriptPath,
        chimney=self.sourceSpecs.sourceInfo.chimney,
      ))
    
    return scriptPath
  # generateArchivalScript()
  
  
  def printTimers(self, out = logging.info):
    out(self.timers.toString(unit="ms", options=('times', 'average')))
    self.scope.printTimers(out)
  # printTimers()
  
  
  def setupSourceSpecs(self):
    return ChimneyReader.makeSourceSpecs(self.readerState.state())
  
  
  def expectedFiles(self, sourceDir = None):
    """Returns a list of all expected CSV files, sorted."""
    
    # we run though all expected reader states in a local loop:
    readerState = ChimneyReader.resetReaderStateSequence(
      chimney=self.readerState.state().chimney,
      N=self.readerState.state().N,
      tests=self.readerState.tests,
      seqClass=self.readerState.__class__,
      )
    sourceSpecs = self.makeSourceSpecs(readerState.state(), sourceDir=sourceDir)
    
    expectedFiles = []
    while True:
      positionFiles = sourceSpecs.allPositionSources(readerState.state().N)
      expectedFiles.extend(positionFiles)
      
      if not readerState.goNext(): break
      sourceSpecs.sourceInfo.connection = readerState.state().cable()
      sourceSpecs.sourceInfo.setPosition(readerState.state().position)
      sourceSpecs.sourceInfo.test = readerState.state().test
    # while
    return expectedFiles
  # expectedFiles()
  
  
  def printFullSequence(self):
    stateSeq = ChimneyReader.resetReaderStateSequence(
     chimney=self.readerState.state().chimney,
     N=self.readerState.state().N,
     tests=self.readerState.tests,
     seqClass=self.readerState.__class__,
     )
    for iStep, state in enumerate(stateSeq):
      print ("[#{}] {}".format(iStep, state))
    else: nSteps = iStep + 1
    print("Total: {} steps.".format(nSteps))
    return nSteps
  # printFullSequence()
  
  
  def _updateSourceInfo(self):
    self.readerState.state().updateWaveformSourceInfo \
      (self.sourceSpecs.sourceInfo)
  # _updateSourceInfo()
  
  def _finalize(self, outputDir, finalOutDir):
    self._finalizeOutputFiles(outputDir)
    if finalOutDir is not None:
      outputDir = self._renameOutputDir(outputDir, finalOutDir)
    self.generateInfoFile(scriptDir=outputDir)
    return outputDir
  # _finalize()
  
  def _start(self, chimney = None, N = None):
    if N is not None: self.readerState.state().N = N
    if chimney is not None: self.readerState.state().setChimney(chimney)
    if not self.readerState.state().hasChimney():
      raise RuntimeError("Start... which chimney??")
    
    ChimneyReader.resetReaderStateSequence(stateSeq=self.readerState)
    
    self.sourceSpecs = self.setupSourceSpecs()
    
    # here we assume that (1) `waveformInfo` is complete enough for the
    # directory name and (2) that name is common to all the files
    tempDir = ChimneyReader.tempDirName(self.sourceSpecs.sourceInfo)
    try: os.makedirs(tempDir)
    except os.error: pass # it exists, which is actually good
    return tempDir
  # _start()
  
  def _finalizeOutputFiles(self, outputDir):
    
    expectedFiles = self.expectedFiles(sourceDir=outputDir)
    nChanged = 0
    import stat
    for file_ in expectedFiles:
      try:
        os.chmod(file_, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        nChanged += 1
      except OSError: pass
    # for
    logging.debug("{}/{} output files made read-only."
      .format(nChanged, len(expectedFiles)))
    return nChanged
  # _finalizeOutputFiles()
  
  
  class ExpectedFileGenerator:
    """Iterates through a list of all expected CSV files, one step per position.
    """
    def __init__(self, reader, sourceDir = None):
      srcState = reader.readerState
      seq = ChimneyReader.resetReaderStateSequence(
        chimney=srcState.state().chimney,
        N=srcState.state().N,
        tests=srcState.tests,
        seqClass=srcState.__class__,
        )
      self.sourceSpecs = reader.makeSourceSpecs \
        (srcState.state(), sourceDir=sourceDir)
      self.seqIter = iter(seq)
    # __init__()
    
    def __iter__(self): return self
    
    def next(self):
      state = next(self.seqIter).state()
      self.sourceSpecs.sourceInfo.connection = state.cable()
      self.sourceSpecs.sourceInfo.setPosition(state.position)
      self.sourceSpecs.sourceInfo.test = state.test
      return self.sourceSpecs.allPositionSources(state.N)
    # next()
    
  # class ExpectedFileGenerator
  
  def expectedFilesPerPosition(self, sourceDir = None):
    return ChimneyReader.ExpectedFileGenerator(self, sourceDir=sourceDir)
  
  
  @staticmethod
  def _renameOutputDir(tempDir, finalDir):
    """Returns the name of `tempDir` after renaming."""
    if not os.path.isdir(tempDir):
      logging.debug("'{}' is not a temporary output directory.".format(tempDir))
      return tempDir
    if ChimneyReader.samefile(tempDir, finalDir):
      logging.debug(
        "Temporary ('{}') and final ('{}') directories are the same."
        .format(tempDir, finalDir)
        )
      return tempDir
    os.rename(tempDir, finalDir)
    logging.info("Temporary output directory '{oldDir}' renamed into '{newDir}'"
      .format(oldDir=tempDir, newDir=finalDir))
    return finalDir
  # _renameOutputDir()
  
  
  @staticmethod
  def finalOutputDirectoryTarget(sourceInfo, outputDir = None):
    """Returns a pair: the name of the directory to check, and the name to
    rename it into (`None` if no renaming should happen)."""
    if outputDir:
      logging.debug(
        "Output directory '{}' was explicitly specified and will not be renamed."
        .format(outputDir)
        )
      return ( outputDir, None )
    # if
    
    outputDir = ChimneyReader.tempDirName(sourceInfo)
    if not os.path.isdir(outputDir):
      # there is no temporary directory: we target the final one, no renaming
      outputDir = ChimneyReader.outputDirName(self.sourceSpecs.sourceInfo)
      logging.debug(
        "Checking the final output directory '{}'; no renaming will happen."
        .format(outputDir)
        )
      return ( outputDir, None )
    # if temporary output directory does not exist
    
    finalOutDir = ChimneyReader.finalOutputDir(sourceInfo)
    if outputDir == finalOutDir:
      # this should not actually happen
      # (unless temporary and final do have the same name, which they do not)
      logging.debug(
        "Output directory '{}' has already the final name and will not be renamed."
        .format(outputDir)
        )
      return ( outputDir, None )
    # if same name
    
    logging.debug(
      "Output directory '{}' may be renamed to '{}'."
      .format(outputDir, finalOutDir)
      )
    
    if not os.path.isdir(outputDir):
      logging.debug(
        "Output directory '{}' appears not to exist. That's going to be trouble."
        .format(outputDir)
        )
      return ( outputDir, finalOutDir ) # what are we talking about here??
    # if
    
    if os.path.exists(finalOutDir) and ChimneyReader.samefile(outputDir, finalOutDir):
      logging.debug(
        "Output directory '{}' is the same as the existing final one '{}'"
        " and will not be renamed."
        .format(outputDir, finalOutDir)
        )
      return ( outputDir, None )
    # if finalize sanity check
    
    return ( outputDir, finalOutDir )
    
  # finalOutputDirectoryTarget()
  
  
  @staticmethod
  def samefile(a, b):
    try: return os.path.samefile(a, b)
    except OSError: return False
  # samefile(a, b)
  
  @staticmethod
  def outputDirName(sourceInfo, temporary = False):
    d = sourceInfo.formatString(ChimneyReader.WaveformDirectory)
    if temporary: d += "_inprogress"
    return d
  # outputDirName()
  
  @staticmethod
  def tempDirName(sourceInfo):
    return ChimneyReader.outputDirName(sourceInfo, temporary=True)
  
  @staticmethod
  def finalOutputDir(sourceInfo):
    return ChimneyReader.outputDirName(sourceInfo, temporary=False)
  
  @staticmethod
  def resetReaderStateSequence(
   stateSeq = None,
   chimney = None, N = None, tests = None,
   seqClass = ReaderStateSequence
   ):
    if stateSeq is None:
      assert chimney is not None
      assert N is not None
      assert tests is not None
      stateSeq = seqClass(ReaderState())
    if chimney is not None: # we are changing the chimney
      stateSeq.state().setChimney(chimney)
    if N is not None: stateSeq.state().N = N # we are changing N
    if tests is not None: stateSeq.setTests(tests) # we are changing tests
    stateSeq.reset()
    return stateSeq
  # resetReaderStateSequence()
  
  
  @staticmethod
  def makeSourceSpecs(readerState, sourceDir = None):
    sourceInfo = drawWaveforms.WaveformSourceInfo(
      chimney=readerState.chimney, connection=readerState.cable(),
      position=readerState.position, channelIndex=1,
      index=readerState.firstIndex(), testName=readerState.test,
      )
    sourceInfo.updateChannel()
    return drawWaveforms.WaveformSourceFilePath(
      sourceInfo,
      filePattern=ChimneyReader.WaveformFilePattern,
      sourceDir=
        (sourceDir if sourceDir is not None else ChimneyReader.tempDirName(sourceInfo)),
      )
  # makeSourceSpecs()
  
  @staticmethod
  def getHostName():
    import socket, os
    try: return socket.getfqdn()
    except: pass
    try: return os.environ.get('HOSTNAME')
    except KeyError: pass
    return "<unknown>"
  # getHostName()
  
  @staticmethod
  def getHostIP():
    import socket
    try: return socket.gethostbyname(socket.getfqdn())
    except: pass
    try: return socket.gethostbyname(socket.gethostname())
    except: pass
    return "<unknown>"
  # getHostIP()
  
  @staticmethod
  def getUserName():
    import getpass
    try: return getpass.getuser()
    except: pass
    try: return os.environ.get('USER')
    except KeyError: pass
    return "<unknown>"
  # getUserName()
  
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
