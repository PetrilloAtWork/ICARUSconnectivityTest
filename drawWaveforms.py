#!/usr/bin/env python

from stopwatch import WatchCollection
import sys
import os
import re
import math
import csv
import logging
import numpy
import struct
from SelectedRange import SelectedRange


################################################################################
def capitalize(word): return word[:1].upper() + word[1:]
def camelCase(*words):
  try: s = words[0]
  except IndexError: return ""
  for word in words[1:]:
    try:
      if s[-1].islower(): word = capitalize(word) 
    except IndexError: pass
    s += word
  # for
  return s
# camelCase()


def inverseLookup(myValue, table):
  for key, value in table.items():
    if myValue == value: return key
  else: raise KeyError(myValue)
# inverseLookup()


def readWaveformTextFile(path):
  # here we keep it very simple...
  columns = [ [], [], ] # start with at least one column
  with open(path, 'r') as f:
    for tokens in csv.reader(f):
      assert len(tokens) == 2
      columns[0].append(float(tokens[0]))
      columns[1].append(float(tokens[1]))
    # for
  # with
  return map(numpy.array, columns)
# readWaveformTextFile()


def writeWaveformTextFile(t, V, path):
  """
  Writes the specified waveform as a CSV text file, each line a `t,V` entry.
  """
  with open(path, 'w') as f:
    for a, b in zip(t, V):
      f.write('{t:g},{V:g}'.format(a, b))
    # for
  # with
  
# writeWaveformTextFile()


DefaultBinaryVersion = 1
class BinaryFileVersion1:
  TimeDataStruct = struct.Struct('<Ldd')
# class BinaryFileVersion1


def readWaveformBinaryFile(path, version = None):
  """
  Reads waveform data from a binary file with specified version.
  
  Formats:
  
  * version 1 (current default):
      * integer: version number
      * integer (`N`): number of sampling points
      * double (C type): sampling of first time
      * double (C type): sampling of last time
      * numpy.float (x `N`): voltage sampled at each of the sampling times, in order
  
  
  Parameters
  -----------
  
  path _(string)_
     path to the input file
  version _(integer, default: autodetect)_
     binary file format (if `None`, it is autodetected);
     see `writeWaveformBinaryFile()` for a description of the formats
  
  
  Returns
  --------
  
  t, V
     iterables of sampling time and sampled voltage
  """
  
  with open(path, 'rb') as inputFile:
    fileVersion = ord(inputFile.read(1))
    if version is None:
      version = fileVersion
    elif version != fileVersion:
      raise RuntimeError(
       "File '{}' is version {} (attempted read as version {})".format(
        path, fileVersion, version
       ))
    # version
    
    if version == 1:
      timeStruct = BinaryFileVersion1.TimeDataStruct
      buf = inputFile.read(timeStruct.size)
      nSamples, minT, maxT = timeStruct.unpack_from(buf)
      t = numpy.linspace(minT, maxT, nSamples)
      V = numpy.fromfile(inputFile, count=nSamples)
      return t, V
    # version 1
    
    raise RuntimeError("Unknown data format: version {}".format(version))
  # with
  
# readWaveformBinaryFile()

def writeWaveformBinaryFile(t, V, path, version = None):
  """
  Writes the specified data into a binary file with specified version.
  
  Formats:
  
  * version 1 (current default):
      * integer: version number
      * integer (`N`): number of sampling points
      * float: sampling of first time
      * float: sampling of last time
      * floats (x `N`): voltage sampled at each of the sampling times, in order
  
  
  Parameters
  -----------
  
  t, V
     lists of sampling time and sampled voltage, to be written
  path _(string)_
     path to the output file; it will be forcibly recreated
  version _(integer, default: latest)_
     binary file format (if `None`, the latest will be picked)
  """
  
  # here we keep it very simple...
  
  if version is None: version = DefaultBinaryVersion
  with open(path, 'wb') as outputFile:
    outputFile.write(chr(version))
    if version == 1:
      timeStruct = BinaryFileVersion1.TimeDataStruct
      outputFile.write(timeStruct.pack(len(t), t[0], t[-1], ))
      V.tofile(outputFile)
      return
    # if version 1
    
    raise RuntimeError("Unknown data format: version {}".format(version))
  # with
# writeWaveformBinaryFile()


def isTextFile(path):
  return os.path.splitext(path)[-1].lower() in [ '.txt', '.csv', ]


def readWaveformFile(path, version = None):
  """
  Reads waveform data from a file.
  
  The input format of the file can be specified (or it will be autodetected).
  Returns two iterables, for time and voltage.
  """
  if version is None and isTextFile(path): version = 0
  if version == 0:
    return readWaveformTextFile(path)
  else:
    return readWaveformBinaryFile(path, version=version)
# readWaveformFile()


def writeWaveformFile(t, V, path, version = None):
  """
  Writes waveform data into a file.
  
  The output format of the file can be specified, or the default binary format
  (`DefaultBinaryVersion`) will be used.
  """
  if version == 0:
    return writeWaveformTextFile(t, V, path)
  else:
    return writeWaveformBinaryFile(t, V, path, version=version)
# readWaveformFile()


def indentText(
 msg,
 indent = "  ",
 firstIndent = None,
 suppressIndentation = False
 ):
  if firstIndent is None: firstIndent = indent
  indentStr = lambda iLine: (firstIndent if iLine == 0 else indent)
  return "\n".join([
    indentStr(iLine) + (line.lstrip() if suppressIndentation else line)
    for iLine, line in enumerate(msg.split('\n'))
    ])
# indentText()

################################################################################
### WaveformSourceInfo: data structure with waveform identification parameters

class ChimneyInfo:
  
  @staticmethod
  def _matchedParsing(match):
    chimneyNumber = match.group(2).lstrip('0')
    return ( match.group(1), int(chimneyNumber) if chimneyNumber else 0, ) \
      if match is not None else None
  # _matchedParsing()
  
  class StyleBase:
    @classmethod
    def split(cls, chimney):
      match = cls.Pattern.match(chimney.upper())
      return ChimneyInfo._matchedParsing(match) if match else None
    @staticmethod
    def format_(row, number):
      return '{row}{number:02d}'.format(row=row.upper(), number=number)
  # StyleBase
  
  class GeographicStyle(StyleBase):
    Name = 'geographic'
    Pattern = re.compile('([EW]{2})([0-9]+)')
    
    StandardTable = { 'EE': 'A', 'EW': 'B', 'WE': 'C', 'WW': 'D', }
    
    @staticmethod
    def fromStandard(row, number):
      return (
        inverseLookup(row, ChimneyInfo.GeographicStyle.StandardTable),
        21 - number,
        )
    # fromStandard()
    
    @staticmethod
    def toStandard(row, number):
      return ( ChimneyInfo.GeographicStyle.StandardTable[row], 21 - number )
    
  # GeographicStyle
  
  class AlphabeticStyle(StyleBase):
    Name = 'alphabetic'
    Pattern = re.compile('([A-D])([0-9]+)')
    
    @staticmethod
    def fromStandard(row, number): return (row, number)
    
    @staticmethod
    def toStandard(row, number): return (row, number)
  
  # AlphabeticStyle
  
  StandardStyle = GeographicStyle
  
  class FlangeStyle(StyleBase):
    Name = 'flange'
    Pattern = re.compile('(F)([0-9]+)')
    
    @staticmethod
    def fromStandard(row, number):
      raise RuntimeError(
        "Special chimney style '{}' can't be converted from a different style"
        .format(ChimneyInfo.FlangeStyle.Name)
        )
    @staticmethod
    def toStandard(row, number):
      raise RuntimeError(
        "Special chimney style '{}' can't be converted to a different style"
        .format(ChimneyInfo.FlangeStyle.Name)
        )
  # FlangeStyle
  
  class InvalidStyle(StyleBase):
    Name = 'invalid'
    Pattern = re.compile('')
    @staticmethod
    def fromStandard(row, number):
      raise RuntimeError(
        "Special chimney style '{}' can't be converted from a different style"
        .format(ChimneyInfo.InvalidStyle.Name)
        )
    @staticmethod
    def toStandard(row, number):
      raise RuntimeError(
        "Special chimney style '{}' can't be converted to a different style"
        .format(ChimneyInfo.InvalidStyle.Name)
        )
  # InvalidStyle
  
  ValidStyles = ( GeographicStyle, AlphabeticStyle, FlangeStyle, )
  
  @staticmethod
  def styleMatcher(chimney):
    for class_ in ChimneyInfo.ValidStyles:
      if class_ is ChimneyInfo.InvalidStyle: continue
      info = class_.split(chimney)
      if not info: continue
      return class_, info
    else: return ChimneyInfo.InvalidStyle, None
  # styleMatcher()
  
  @staticmethod
  def split(chimney):
    style, info = ChimneyInfo.styleMatcher(chimney)
    if info is None:
      raise RuntimeError("'{}' is not a valid chimney.".format(chimney))
    return info + tuple([ style, ])
  # split()
  
  @staticmethod
  def format_(series, n): return "{}{:02d}".format(series, n)
  
  @staticmethod
  def isChimney(chimney):
    return ChimneyInfo.splitChimney(chimney.upper()) is not None
  
  @staticmethod
  def detectStyle(chimney):
    style, _ = ChimneyInfo.styleMatcher(chimney)
    return style.Name
  # detectStyle()
  
  @staticmethod
  def expandStyle(style):
    try: isStyle = issubclass(style, ChimneyInfo.StyleBase)
    except TypeError: isStyle = False
    if isStyle:
      styleName = style.Name
    else:
      styleName = style
      style = ChimneyInfo.findStyle(styleName)
      if style is None:
        raise RuntimeError("Chimney name style '{}' invalid".format(styleName))
    return style, styleName
  # expandStyle()
  
  @staticmethod
  def convertToStyleAndSplit(style, chimney, srcStyle = None):
    style, styleName = ChimneyInfo.expandStyle(style)
    if not srcStyle: # autodetect original style
      srcStyle, info = ChimneyInfo.styleMatcher(chimney)
      if srcStyle is ChimneyInfo.InvalidStyle:
        raise RuntimeError("'{}' is not a valid chimney.".format(chimney))
      row, number = info
    else:
      srcStyle, _ = ChimneyInfo.expandStyle(srcStyle)
      row, number = srcStyle.split(chimney)
    #
    if srcStyle is not style:
      row, number = srcStyle.toStandard(row, number)
      row, number = style.fromStandard(row, number)
    return (row, number)
  # convertToStyleAndSplit()
  
  @staticmethod
  def convertToStyle(style, chimney, srcStyle = None):
    style, _ = ChimneyInfo.expandStyle(style)
    return style.format_ \
      (*ChimneyInfo.convertToStyleAndSplit(style, chimney, srcStyle=srcStyle))
  # convertToStyle()
  
  @staticmethod
  def findStyle(styleName):
    for style in ChimneyInfo.ValidStyles:
      if style.Name.lower() == styleName.lower(): return style
    else: return None
  # findStyle()
  
  @staticmethod
  def _matchedParsing(match):
    chimneyNumber = match.group(2).lstrip('0')
    return ( match.group(1), int(chimneyNumber) if chimneyNumber else 0, ) \
      if match is not None else None
  # _matchedParsing()
  
# class ChimneyInfo

class CableInfo:
  
  Pattern = re.compile('([A-Z]?)([0-9]{1,2})')
  
  @staticmethod
  def isCable(cable):
    return CableInfo.Pattern.match(cable.upper()) is not None
  
  @staticmethod
  def parse(cable):
    match = CableInfo.Pattern.match(cable.upper())
    if match is None:
      raise RuntimeError("'{}' is not a valid cable identifier.")
    
    cableNumber = match.group(2).lstrip('0')
    cableTag = match.group(1)
    return cableTag, int(cableNumber)
  # parse()
  
  @staticmethod
  def extract(cable, chimney = None):
    cableTag, cableNumber = CableInfo.parse(cable)
    if not cableTag:
      if chimney is None:
        raise RuntimeError \
         ("A chimney is required in order to parse cable identifier '{}'")
      # if
      cableTag = CableInfo.tagFor(chimney)
    # if
    return cableTag, cableNumber
  # extract()
  
  @staticmethod
  def format_(cableTag, cableNo, chimney = None):
    if not cableTag:
      if chimney is None:
        raise RuntimeError(
         "Either cable tag or chimney are required for formatting a cable name."
         )
      cableTag = CableInfo.tagFor(chimney)
    # if not cableTag
    return "{tag}{no:02d}".format(tag=cableTag, no=cableNo)
  # format_()
  
  
  @staticmethod
  def tagFor(chimney):
    chimneySeries, chimneyNo = ChimneyInfo.convertToStyleAndSplit \
      (ChimneyInfo.StandardStyle, chimney)
    if chimneySeries in [ 'EE', 'WE', ]:
      if   chimneyNo == 1:  return 'D'
      elif chimneyNo == 20: return 'C'
      else:                 return 'V'
    elif chimneySeries in [ 'EW', 'WW', ]:
      if   chimneyNo == 1:  return 'B'
      elif chimneyNo == 20: return 'A'
      else:                 return 'S'
    elif chimneySeries == "F": return 'V'
    raise RuntimeError("No cable tag for chimneys '{}'".format(chimneySeries))
  # tagFor()
  
# class CableInfo



class WaveformSourceInfo:
  
  MaxChannels = 4
  MaxPositions = 8
  # it should be `MaxChannels`, but it's already taken:
  TotalChannels = MaxChannels * MaxPositions
  
  def __init__(self,
   chimney=None, connection=None, channelIndex=None, position=None,
   index=None,
   testName="",
   ):
    self.test         = testName
    self.chimney      = chimney
    self.connection   = connection
    self.position     = position
    self.channelIndex = channelIndex
    self.index        = index
    self.updateChannel()
    self.updateConnection()
  # __init__()
  
  def copy(self):
    return WaveformSourceInfo(
      chimney=self.chimney, connection=self.connection,
      channelIndex=self.channelIndex, position=self.position,
      index=self.index, testName=self.test,
      )
  # copy()
  
  def formatString(self, s): return s % vars(self)
  
  def setChimney(self, chimney):
    self.chimney = chimney
    self.updateConnection()
  def setConnection(self, connection):
    self.connection = connection
    self.updateConnection()
  def setChannelIndex(self, channelIndex):
    self.channelIndex = channelIndex
    self.updateChannel()
  def setPosition(self, position):
    self.position = position
    self.updateChannel()
  def setChannel(self, channel):
    self.channel = channel
    self.updatePositionAndChannelIndex()
  def setIndex(self, index): self.index = index
  def setFirstIndex(self, N = 10):
    self.setIndex(self.firstIndexOf(self.position, N=N))
  def increaseIndex(self, amount = 1): self.index += amount
  
  def updateChannel(self):
    self.channel = \
      None if self.position is None or self.channelIndex is None \
      else (self.position - 1) * WaveformSourceInfo.MaxChannels + self.channelIndex
  # updateChannel()
  def updatePositionAndChannelIndex(self):
    self.position = None if self.channel is None \
      else WaveformSourceInfo.positionOfChannel(self.channel)
    self.channelIndex = None if self.channel is None \
      else WaveformSourceInfo.indexOfChannel(self.channel)
  # updatePositionAndChannelIndex()
  def updateConnection(self):
    if (self.chimney is None) or (self.connection is None): return
    cableTag, cableNo = CableInfo.extract(self.connection, chimney=self.chimney)
    self.connection = CableInfo.format_(cableTag, cableNo)
  # updateConnection()
  
  @staticmethod
  def firstIndexOf(position, N = 10): return (position - 1) * N + 1
  
  @staticmethod
  def indexOfChannel(channel):
    return ((channel - 1) % WaveformSourceInfo.MaxChannels) + 1
  @staticmethod
  def positionOfChannel(channel):
    return ((channel - 1) // WaveformSourceInfo.MaxChannels) + 1
  
# class WaveformSourceInfo


################################################################################
### `WaveformSourceFilePath`: waveform parameter management

class WaveformSourceFilePath:
  
  StandardDirectory = "CHIMNEY_%(chimney)s"
  StandardPattern = "%(test)swaveform_CH%(channelIndex)d_CHIMNEY_%(chimney)s_CONN_%(connection)s_POS_%(position)d_%(index)d.csv"
  
  def __init__(self,
   sourceInfo, filePattern = StandardPattern, sourceDir = ".",
   ):
    """
    The expected pattern is:
    
    "path/HVwaveform_CH3_CHIMNEY_A11_CONN_V12_POS_7_62.csv"
    
    """
    self.sourceDir = sourceDir
    self.sourceFilePattern = filePattern
    self.sourceInfo = sourceInfo
    self.sourceInfo.updateChannel()
  # __init__()
  
  def copy(self):
    return self.__class__(
      self.sourceInfo.copy(),
      filePattern=self.sourceFilePattern,
      sourceDir=self.sourceDir,
      )
  # copy()
  
  def setSourceInfo(self, sourceInfo): self.sourceInfo = sourceInfo
  
  def formatString(self, s):
    info = vars(self).copy()
    info.update(vars(self.sourceInfo))
    return s % info
  # formatString()
  
  def buildPath(self):
    return os.path.join(self.sourceDir, self.formatString(self.sourceFilePattern))
  
  def describe(self):
    msg = "Source directory: '%s'\nPattern: '%s'" % (self.sourceDir, self.sourceFilePattern)
    msg += "\nTriggering file: '" + os.path.join(self.sourceDir, self.sourceFilePattern % vars(self.sourceInfo)) + "'"
    return msg
  # describe()
  
  def allChannelSources(self, channelIndex = None, channel = None, N = 10):
    """
    Returns the list of N expected waveform files at the specified channel index.
    """
    values = self.sourceInfo.copy()
    if channelIndex is not None:
      values.setChannelIndex(channelIndex)
      assert channel is None
    elif channel is not None:
      values.setChannel(channel)
      assert channelIndex is None
    values.setIndex((self.sourceInfo.position - 1) * N)
    
    files = []
    for i in xrange(N):
      values.increaseIndex()
      files.append(os.path.join(self.sourceDir, self.sourceFilePattern % vars(values)))
    # for i
    return files
  # allChannelSources()
  
  def allPositionSources(self, N = 10):
    """Returns the list of 4N expected waveform files for the current position."""
    files = []
    for channelIndex in xrange(1, WaveformSourceInfo.MaxChannels + 1): files.extend(self.allChannelSources(channelIndex=channelIndex, N=N))
    return files
  # allPositionSources()
  
# class WaveformSourceFilePath


def parseWaveformSource(path):
  """Parses `path` and returns a filled `WaveformSourceFilePath`.
  
  The expected pattern is:
  
  "path/PULSEwaveform_CH3_CHIMNEY_EE11_CONN_V12_POS_7_62.csv"
  
  """
  sourceDir, triggerFileName = os.path.split(path)
  
  name, ext = os.path.splitext(triggerFileName)
  if ext.lower() != '.csv':
    print >>sys.stderr, "Warning: the file '%s' has not the name of a comma-separated values file (CSV)." % path
  tokens = name.split("_")
  
  sourceInfo = WaveformSourceInfo()
  
  sourceFilePattern = []
  
  iToken = 0
  while iToken < len(tokens):
    Token = tokens[iToken]
    iToken += 1
    TOKEN = Token.upper()
    
    if TOKEN == 'CHIMNEY':
      try: sourceInfo.setChimney(tokens[iToken])
      except IndexError:
        raise RuntimeError("Error parsing file name '%s': no chimney." % triggerFileName)
      iToken += 1
      sourceFilePattern.extend([ Token, "%(chimney)s", ])
      continue
    elif TOKEN == 'CONN':
      try: sourceInfo.setConnection(tokens[iToken])
      except IndexError:
        raise RuntimeError("Error parsing file name '%s': no connection code." % triggerFileName)
      iToken += 1
      sourceFilePattern.extend([ Token, "%(connection)s", ])
      continue
    elif TOKEN == 'POS':
      try: sourceInfo.position = int(tokens[iToken])
      except IndexError:
        raise RuntimeError("Error parsing file name '%s': no connection code." % triggerFileName)
      except ValueError:
        raise RuntimeError("Error parsing file name '%s': '%s' is not a valid position." % (triggerFileName, tokens[iToken]))
      sourceFilePattern.extend([ Token, "%(position)s", ])
      iToken += 1
      continue
    elif TOKEN.endswith('WAVEFORM'):
      testName = Token[:-len('WAVEFORM')]
      channel = tokens[iToken]
      if not channel.startswith('CH'):
        raise RuntimeError("Error parsing file name '%s': '%s' is not a valid channel." % (triggerFileName, channel))
      try: sourceInfo.setChannelIndex(int(channel[2:]))
      except IndexError:
        raise RuntimeError("Error parsing file name '%s': no connection code." % triggerFileName)
      except ValueError:
        raise RuntimeError("Error parsing file name '%s': '%s' is not a valid channel number." % (triggerFileName, channel[2:]))
      sourceFilePattern.extend([ Token, "CH%(channelIndex)d", ])
      iToken += 1
      continue
    else:
      try:
        sourceInfo.setIndex(int(Token))
        sourceFilePattern.append('%(index)d')
      except ValueError:
        print >>sys.stderr, "Unexpected tag '%s' in file name '%s'" % (Token, triggerFileName)
        sourceFilePattern.append(Token)
    # if ... else
  # while
  
  if sourceInfo.chimney is None: raise RuntimeError("No chimney specified in file name '%s'" % triggerFileName)
  if sourceInfo.connection is None: raise RuntimeError("No connection specified in file name '%s'" % triggerFileName)
  if sourceInfo.position is None: raise RuntimeError("No position specified in file name '%s'" % triggerFileName)
  if sourceInfo.channelIndex is None: raise RuntimeError("No channel specified in file name '%s'" % triggerFileName)
  if sourceInfo.index is None: raise RuntimeError("No index specified in file name '%s'" % triggerFileName)
  
  sourceInfo.updateChannel()
  sourceFilePattern = "_".join(sourceFilePattern)
  if ext: sourceFilePattern += ext
  
  return WaveformSourceFilePath(sourceInfo, sourceFilePattern, sourceDir)
  
# parseWaveformSource()
  


def readWaveform(filePath):
  
  columns = [ [], [] ]
  with open(filePath, 'r') as inputFile:
    for line in inputFile:
      valueStrings = line.strip().split(",")
      #
      # columns = [ Xlist, Ylist ]
      # valueStrings = [ Xvalue, Yvalue ]
      # zip(columns, valueStrings) = ( ( Xlist, Xvalue ), ( Ylist, Yvalue ) )
      #
      for values, newValue in zip(columns, valueStrings):
        values.append(float(newValue))
    # for
  # with
  return columns
  
# readWaveform() 


################################################################################
### Statistics

class ExtremeAccumulatorBase:
  def __init__(self, comparer = (lambda a, b: a < b)):
    self.extreme = None
    self.comparer = comparer
  def add(self, value):
    if (self.extreme is None) or self.comparer(value, self.extreme):
      self.extreme = value
      return True
    else: return False
  # add()
  def __call__(self): return self.extreme
# class ExtremeAccumulator

class MinAccumulator(ExtremeAccumulatorBase):
  def __init__(self):
    ExtremeAccumulatorBase.__init__(self, comparer=(lambda a, b: a < b))
# class MinAccumulator

class MaxAccumulator(ExtremeAccumulatorBase):
  def __init__(self):
    ExtremeAccumulatorBase.__init__(self, comparer=(lambda a, b: a > b))
# class MaxAccumulator

class ExtremeAccumulator:
  def __init__(self):
    self.min = MinAccumulator()
    self.max = MaxAccumulator()
  def add(self, value):
    self.min.add(value)
    self.max.add(value)
# class ExtremeAccumulator


class ExtremeAccumulatorNbase:
  
  def __init__(self, N, comparer = (lambda a, b: a < b)):
    self.N = N
    self.selected = []
    self.comparer = comparer
  # __init__()
  
  def add(self, v):
    if not self.selected:
      self.selected.append(v)
      return True
    if not self.comparer(v, self.selected[-1]): return False
    self.selected.append(v)
    self.selected.sort(self.comparer)
    self.selected = self.selected[:self.N]
    return True
  # add()
  
  def __call__(self): return self.selected
  
# ExtremeAccumulatorNbase()

class MinAccumulatorN(ExtremeAccumulatorNbase):
  def __init__(self, N):
    ExtremeAccumulatorNbase.__init__(self, N, comparer=(lambda a, b: a < b))
# class MinAccumulatorN

class MaxAccumulatorN(ExtremeAccumulatorNbase):
  def __init__(self, N):
    ExtremeAccumulatorNbase.__init__(self, N, comparer=(lambda a, b: a > b))
# class MaxAccumulatorN

class ExtremeAccumulatorN:
  def __init__(self, N):
    self.min = MinAccumulatorN(N)
    self.max = MaxAccumulatorN(N)
  def add(self, v):
    self.min.add(v)
    self.max.add(v)
# class ExtremeAccumulatorN


class StatAccumulator:
  
  def __init__(self):
    self.n   = 0
    self.w   = 0.0
    self.wx  = 0.0
    self.wx2 = 0.0
  # __init__()
  
  def add(self, v, w = 1.0):
    self.n   += 1
    self.w   += w
    self.wx  += w * v
    self.wx2 += w * v**2
  # add()
  
  def merge(self, other):
    self.n   += other.n
    self.w   += other.w
    self.wx  += other.wx
    self.wx2 += other.wx2
  # merge()
  
  def average(self):
    return self.wx / self.w
  def averageError(self):
    return self.RMS() / math.sqrt(self.w)
  def averageSquares(self):
    return self.wx2 / self.w
  def RMS(self):
    return math.sqrt(max(self.averageSquares() - self.average()**2, 0.0))
  
# class StatAccumulator


################################################################################
### Waveform analysis

def findMaximum(t, V):
  """Simple peak finder, returns the position of the maximum value."""
  
  # let's start simple:
  maxVal = MaxAccumulator()
  maxPos = None
  
  for i, x in enumerate(V):
    if maxVal.add(x): maxPos = i
  
  return maxPos
# findMaximum()

def findMinimum(t, V):
  """Simple peak finder, returns the position of the minimum value."""
  
  minVal = MinAccumulator()
  minPos = None
  
  for i, x in enumerate(V):
    if minVal.add(x): minPos = i
  
  return minPos
# findMinimum()


def findExtremes(t, V):
  """Simple peak finder, returns the position of the minimum and maximum values."""
  
  minVal = MinAccumulator()
  minPos = None
  maxVal = MaxAccumulator()
  maxPos = None
  
  for i, x in enumerate(V):
    if minVal.add(x): minPos = i
    if maxVal.add(x): maxPos = i
  
  return (minPos, maxPos)
# findExtremes()


def extractBaselineFromPedestal(t, V, iPeak, iDip):
  result = { 'status': 'good', }
  margin = int( (iPeak-iDip)/2 )
  iEnd = iDip - margin
  dV = V[iPeak] - V[iDip]
  if ( dV < 0.15 ): iEnd = len(V)
  elif iEnd < 10:
    result['status'] = 'peakTooLow'
    print >> sys.stderr, 'This difference between maximum and minimum is %f while minimum is at time %f (tick %d) and maximum is at %f (tick %d)' %( dV, t[iDip], iDip, t[iPeak], iPeak )
    iEnd = len(V)
  elif margin < 0:
    result['status'] = 'swappedPeaks'
    print >> sys.stderr, 'This difference between maximum and minimum is %f while minimum is at time %f (tick %d) and maximum is at %f (tick %d)' %( dV, t[iDip], iDip, t[iPeak], iPeak )
    iEnd = len(V)
  
  stats = StatAccumulator()
  for i in xrange(iEnd):
    stats.add(V[i])
    # print i, iEnd
  
  result.update({
    'value': stats.average(), 'error': stats.averageError(), 'RMS': stats.RMS(),
    })
  return result
  
# extractBaselineFromPedestal()


def extractBaseline(t, V):
  """Baseline extractor algorithm.
  
  A distribution is generated for all sampled signal values.
  The central 50% of the distribution is taken, and the average and RMS of the
  elements in that range make up the baseline and noise.
  """
  
  margin = int(0.25 * len(V)) # on each side
  
  stats = StatAccumulator()
  for x in sorted(V)[margin:-margin]: stats.add(x)
  
  return {
    'value': stats.average(), 'error': stats.averageError(), 'RMS': stats.RMS(),
    }
  
# extractBaseline()


def extractPeaks(t, V, baseline = 0.0, l = 1):
  """Peak finder with running window average.

  The peaks are found as extrema of the averages of `l` elements in a running window.
  If specified, a baseline is subtracted to all samples.

  V is required to have at least one element.
  Samples are assumed to be periodic.
  
  """

  assert l >= 1
  assert len(V) >= l
  
  minSum = MinAccumulator()
  minPos = None
  maxSum = MaxAccumulator()
  maxPos = None
  
  iterV = iter(V)
  s = 0.0
  for i, v in enumerate(iterV):
    if i >= l: break
    s += v
  last = 0
  for i, x in enumerate(iterV, start=l):
    s += x - last
    if minSum.add(s): minPos = i
    if maxSum.add(s): maxPos = i
    last = V[i]
  # for i

  minStats = [ StatAccumulator(), StatAccumulator(), ]
  for x, y in zip(t, V)[minPos:minPos + l]:
    minStats[0].add(x)
    minStats[1].add(y)

  maxStats = [ StatAccumulator(), StatAccumulator(), ]
  for x, y in zip(t, V)[maxPos:maxPos + l]:
    maxStats[0].add(x)
    maxStats[1].add(y)

  return {
    'positive': { 'value': maxStats[1].average() - baseline, 'valueError': maxStats[1].RMS(), 'time': maxStats[0].average(), 'timeError': maxStats[0].RMS(), },
    'negative': { 'value': minStats[1].average() - baseline, 'valueError': minStats[1].RMS(), 'time': minStats[0].average(), 'timeError': minStats[0].RMS(), },
    }
# extractPeaks()


def extractStatistics(t, V):
  stats = {}
  
  iMax = findMaximum(t, V)
  stats['maximum'] = { 'value': V[iMax], 'time': t[iMax], 'pos': iMax, }
  
  iMin = findMinimum(t, V)
  stats['minimum'] = { 'value': V[iMin], 'time': t[iMin], 'pos': iMin, }
  
  stats['baseline'] = extractBaseline(t, V)
  
  # while the peaks look sharp to the eye, they're spread across many samples;
  stats['peaks'] = extractPeaks(t, V, stats['baseline']['value'], 5)
  absPeak = stats['peaks']['positive' if abs(stats['peaks']['positive']['value']) > abs(stats['peaks']['negative']['value']) else 'negative']
  
  stats['peaks']['absolute'] = {
    'value': abs(absPeak['value']),
    'valueError': abs(absPeak['valueError']),
    'time': absPeak['time'],
    'timeError': absPeak['timeError'],
    }
  
  return stats
# extractStatistics()


################################################################################
### Waveform drawing
################################################################################

class VirtualRenderer:
  
  def __init__(self): pass
  
  def makeWaveformCanvas(self, canvasName, nPads, options = {}, canvas = None):
    return None
  
  def selectPad(self, iPad, canvas = None): pass
  
  def plotFromFile(self, filePath):
    """
    Returns the plot object and data on X and on Y axes as iterable collections.
    """
    return None, [], [],
  
  def graphPoints(self, graph): return 0
  
  def setGraphVerticalRange(self, graph, min, max): pass
  
  def SetRedBackgroundColor(self, canvas): pass
  
  def makeMultiplot(self, name, title): return None
  
  def addPlotToMultiplot(self, graph, mgraph, color): pass
  
  def setObjectNameTitle(self, obj, name, title): pass
  
  def drawWaveformsOnCanvas(self, graph, canvas = None): pass
  
  def drawLegendOnCanvas(self, legendLines, boxName, canvas = None):
    return None
  
  def finalizeCanvas(self, canvas, title): pass

  def updateCanvas(self, canvas): pass
  
  def baseColors(self): return tuple([ 0, ])
  
  def saveCanvasAs(self, *formats): pass
  
  def pause(self):
    print "Press <Enter> to continue."
    sys.stdin.readline()
  # pause()
  
# class VirtualRenderer

################################################################################
class NullRenderer(VirtualRenderer):
  
  def plotFromFile(self, filePath):
    columns = readWaveformFile(filePath)
    return None, columns[0], columns[1],
  # plotFromFile()
  
# class NullRenderer

################################################################################
class MPLRendering:
  
  def __init__(self):
    raise NotImplementedError("matplotlib rendering has not been implemented yet")
  
  def makeWaveformCanvas(self, canvasName, nPads, options = {}, canvas = None):
    return None
  
  def selectPad(self, iPad, canvas = None): pass
  
  def plotFromFile(self, filePath): return None, [], [],
  
  def graphPoints(self, graph): return 0
  
  def setGraphVerticalRange(self, graph, min, max): pass
  
  def SetRedBackgroundColor(self, canvas): pass
  
  def makeMultiplot(self, name, title): return None
  
  def addPlotToMultiplot(self, graph, mgraph, color): pass
  
  def setObjectNameTitle(self, obj, name, title): pass
  
  def drawWaveformsOnCanvas(self, graph, canvas = None): pass
  
  def drawLegendOnCanvas(self, legendLines, boxName, canvas = None):
    return None
  
  def finalizeCanvas(self, canvas, title): pass
  
  def updateCanvas(self, canvas): pass
  
  def baseColors(self): return tuple([ 0, ])
  
  def saveCanvasAs(self, *formats): pass

# class MPLRendering

################################################################################
class ProtectArguments:
  def __init__(self): self.args = sys.argv
  def __enter__(self): sys.argv = [ self.args[0] ]
  def __exit__(self, exc_type, exc_value, traceback): sys.argv = self.args
# class ProtectArguments

class ROOTrendering(VirtualRenderer):
  
  @staticmethod
  def detachObject(obj):
    ROOTrendering.ROOT.SetOwnership(obj, False)
    return obj
  # detachObject()
  
  def __init__(self):
    with ProtectArguments():
      try: import ROOT
      except ImportError: ROOT = None
    ROOTrendering.ROOT = ROOT
    if not ROOT:
      raise RuntimeError \
        ("ROOT not available: can't instantiate `ROOTrendering` class.")
  # __init__()
  
  def plotFromFile(self, filePath):
    graph = self.ROOT.TGraph(filePath, '%lg,%lg')
    return graph, graph.GetX(), graph.GetY()
  
  def graphPoints(self, graph): return graph.GetN()
  
  def setGraphVerticalRange(self, graph, min, max):
    graph.GetYaxis().SetRangeUser(min, max)
  
  def SetRedBackgroundColor(self, canvas):
    self.ROOT.gPad.SetFillColor(self.ROOT.kRed)
  
  def makeWaveformCanvas(self,
   canvasName,
   nPads,
   options = {},
   canvas = None, # reuse
   ):
    if not canvas:
      canvas = self.ROOT.TCanvas(canvasName, canvasName)
    else:
      canvas.cd()
      canvas.Clear()
      canvas.SetName(canvasName)
    self.detachObject(canvas)
    if options.get("grid", "square").lower() in [ "square", "default", ]:
      canvas.DivideSquare(nPads)
    elif options["grid"].lower() == "vertical":
      canvas.Divide(1, nPads)
    elif options["grid"].lower() == "horizontal":
      canvas.Divide(nPads, 1)
    else:
      raise RuntimeError("Option 'grid' has unrecognised value '%s'" % options['grid'])
    
    for channelIndex in range(1, nPads + 1):
      #
      # pad graphic options preparation
      #
      pad = canvas.cd(channelIndex)
      pad.SetFillColor(self.ROOT.kWhite)
      pad.SetLeftMargin(0.08)
      pad.SetRightMargin(0.03)
      pad.SetBottomMargin(0.06)
      pad.SetGridx()
      pad.SetGridy()
    # for
    
    canvas.cd()
    return canvas
  # makeWaveformCanvas()
  
  def selectPad(self, iPad, canvas = None):
    canvas.cd(iPad + 1)
  
  def makeMultiplot(self, name, title):
    mgraph = self.ROOT.TMultiGraph()
    mgraph.SetName(name)
    mgraph.SetTitle(title)
    return mgraph
  # makeMultiplot()
  
  def addPlotToMultiplot(self, graph, mgraph, color):
    self.detachObject(graph)
    graph.SetLineColor(color)
    mgraph.Add(graph, "L")
  # addPlotToMultiplot()
  
  def setObjectNameTitle(self, obj, name, title):
    obj.SetNameTitle(name, title)
  
  def drawWaveformsOnCanvas(self, graph, canvas = None):
    self.detachObject(graph)
    if canvas: canvas.cd()
    graph.Draw("A")
    
    #
    # setting (multi)graph graphic options
    #
    xAxis = graph.GetXaxis()
    xAxis.SetDecimals()
    xAxis.SetTitle("time  [s]")
    # set the range to a minimum
    yAxis = graph.GetYaxis()
    yAxis.SetDecimals()
    yAxis.SetTitle("signal  [V]")
    
  # drawWaveformsOnCanvas()
  
  def drawLegendOnCanvas(self, legendLines, boxName, canvas = None):
    if canvas: canvas.cd()
    
    # "none" is a hack: `TPaveText` deals with NDC and removes it from the
    # options, then passes the options to `TPave`; if `TPave` finds an empty
    # option string (as it does when the original option was just "NDC"), it
    # sets a "br" default; but ROOT does not punish the presence of
    # unsupported options.
    statBox = self.detachObject(self.ROOT.TPaveStats
      (0.60, 0.80 - 0.025*len(legendLines), 0.98, 0.92, "NDC none"))
    statBox.SetOptStat(0); # do not print title (the other flags are ignored)
    statBox.SetBorderSize(1)
    statBox.SetName(boxName)
    for statText in legendLines: statBox.AddText(statText)
    statBox.SetFillColor(self.ROOT.kWhite)
    statBox.SetTextFont(42) # regular (not bold) sans serif, scalable
    statBox.Draw()
    return statBox
  # drawLegendOnCanvas()
  
  def finalizeCanvas(self, canvas, title):
    canvas.cd(0)
    canvas.SetTitle(title)
    canvas.Draw()
    canvas.Update()
  # finalizeCanvas()
  
  def updateCanvas(self, canvas): canvas.Update()
  
  def saveCanvasAs(self, *formats):
    if not formats: return
    if len(formats) > 1: # poor man recursion
      self.saveCanvasAs(formats[0])
      self.saveCanvasAs(*formats[1:])
      return
    format_ = formats[0]
    self.currentCanvas().SaveAs \
     (self.currentCanvas().GetName() + "." + format_.lstrip('.'))
  # saveCanvasAs()
  
  def currentCanvas(self): return self.ROOT.gPad
  
  def baseColors(self):
    ROOT = ROOTrendering.ROOT
    return (
      ROOT.kBlack,
      ROOT.kYellow + 1,
      ROOT.kCyan + 1,
      ROOT.kMagenta + 1,
      ROOT.kGreen + 1
      )
  # baseColors()
  
# class ROOTrendering

################################################################################
RenderOptions = {
  None:         { 'name': 'none',         'rendererClass': NullRenderer, },
  'NONE':       { 'name': 'none',         'rendererClass': NullRenderer, },
  'ROOT':       { 'name': 'ROOT',         'rendererClass': ROOTrendering, },
  'MATPLOTLIB': { 'name': 'matplotlib',   'rendererClass': MPLRendering, },
}
Renderer = None

def useRenderer(rendererName):
  try:
    RendererInfo \
      = RenderOptions[None if rendererName is None else rendererName.upper() ]
  except KeyError:
    raise RuntimeError("Unsupported renderer: {}".format(rendererName))
  global Renderer
  Renderer = RendererInfo['rendererClass']()
  return RendererInfo['name']
# useRenderer()


def plotWaveformFromFile(filePath, sourceInfo = None):
  
  if not os.path.exists(filePath):
    print >>sys.stderr, "Can't plot data from '%s': file not found." % (filePath)
    return None, [], []
  graph, X, Y = Renderer.plotFromFile(filePath)
  logging.debug("'{file}': {points} points"
    .format(file=filePath, points= Renderer.graphPoints(graph))
    )
  if sourceInfo is None: sourceInfo = parseWaveformSource(filePath).sourceInfo
  graphName = sourceInfo.formatString("GWaves_Chimney%(chimney)s_Conn%(connection)s_Ch%(channel)d_I%(index)d")
  graphTitle = sourceInfo.formatString("Chimney %(chimney)s connection %(connection)s channel %(channel)d (%(index)d)")
  Renderer.setObjectNameTitle(graph, graphName, graphTitle)
  return graph, X, Y
  
# plotWaveformFromFile()


def plotSingleChannel(sourceSpecs, options = {}):
  """
  Draws on the current canvas a plot of all waveforms on the same channel.
  
  Options:
  * 'graphColor': override the color of the plots
  * 'printStats': prints the collected statistics to console
  * 'timers': a timer manager; will use:
      * 'channel': pretty much everything except printing statistics
      * 'graph': creation of the graph (includes reading the input sources)
      * 'stats': statistics collection
      * 'draw': final rendering of the plots to the canvas
      * 'drawstats': statistics rendering on the canvas
  """
  #
  # The `ROOT.SetOwnership()` calls free the specified ROOT objects from python
  # garbage collection scythe. We need that because since we created them,
  # we own them, and drawing them does not leave references behind that could
  # keep them around.
  #
  # We know the voltage range we expect the waveforms in, which is roughly
  # 2.0 +/- 0.9 V; so we draw within this range, unless it would cut the
  # waveform. We also leave some room for the eye.
  defYamplitude = 0.9
  defYmargin = 0.1
  
  timers = options.get('timers', WatchCollection(title="`plotAllPositionWaveforms()`: timings"))
  N = options.get('N', 10)
  
  sourceSpecs = sourceSpecs.copy() # do not mess with the passed one
  channelSourceInfo = sourceSpecs.sourceInfo
  channelSourceInfo.setFirstIndex(N=N)
  
  baseColors = Renderer.baseColors()
  
  channel = channelSourceInfo.channel
  sys.stderr.write(" Ch{:d}".format(channel))
  
  with timers.setdefault('channel', description="channel plot time"):
    
    baseColor = options.get \
      ('graphColor', baseColors[channelSourceInfo.channelIndex % len(baseColors)])
    
    graphName = channelSourceInfo.formatString \
      ("MG_%(chimney)s_%(connection)s_Ch%(channel)d")
    graphTitle = channelSourceInfo.formatString \
      ("Chimney %(chimney)s connection %(connection)s channel %(channel)s")
    mgraph = Renderer.makeMultiplot(name=graphName, title=graphTitle)
    
    #
    # drawing all waveforms and collecting statistics
    #
    baselineStats = StatAccumulator()
    baselineRMSstats = StatAccumulator()
    maxStats = StatAccumulator()
    peakStats = StatAccumulator()
    Vrange = ExtremeAccumulator()
    
    iSource = 0
    sourcePaths = sourceSpecs.allChannelSources \
     (channelIndex=channelSourceInfo.channelIndex, N=N)
    for sourcePath in sourcePaths:
      with timers.setdefault('graph', description="graph creation"):
        graph, X, Y = plotWaveformFromFile(sourcePath, sourceInfo=channelSourceInfo)
        if not graph: continue
        Renderer.addPlotToMultiplot(graph, mgraph, baseColor)
      # with graph timer
      
      with timers.setdefault('stats', description="statistics extraction"):
        stats = extractStatistics(X, Y)
        baselineStats.add(stats['baseline']['value'], w=stats['baseline']['error'])
        baselineRMSstats.add(stats['baseline']['RMS'])
        maxStats.add(stats['maximum']['value'])
        peakStats.add(stats['peaks']['absolute']['value'])
        Vrange.add(stats['maximum']['value'])
        Vrange.add(stats['minimum']['value'])
      # with stats timer
      
      sys.stderr.write('.')
      iSource += 1
    # for
    else: nWaveforms = iSource 
    
    if nWaveforms == 0: return None
    
    with timers.setdefault('draw', description="multigraph drawing"):
      Renderer.drawWaveformsOnCanvas(mgraph)
    # with draw timer
      
    with timers.setdefault('drawstats', description="statistics drawing"):
      # instead of hard-coding the expected baseline of ~2.0 we use the actual
      # baseline average, rounded at 100 mV (one decimal digit)
      drawBaseline = round(baselineStats.average(), 1)
      Ymin = drawBaseline - defYamplitude
      Ymax = drawBaseline + defYamplitude
      if (Vrange.min() >= Ymin and Vrange.max() <= Ymax):
        Renderer.setGraphVerticalRange \
          (mgraph, Ymin - defYmargin, Ymax + defYmargin)
      # if
      
      #
      # statistics box
      #
      statsText = [
        "waveforms = %d" % nWaveforms,
        "baseline = %.3f V (RMS %.3f V)" % (baselineStats.average(), baselineRMSstats.average()),
        "maximum = (%.3f #pm %.3f) V" % (maxStats.average(), maxStats.averageError()),
        "peak = %.3f V (RMS %.3f V)" % (peakStats.average(), peakStats.RMS())
        ]
      Renderer.drawLegendOnCanvas(statsText, graphName + "_stats")
    # with drawstats timer
    
  # with channel timer
  
  if options.get('printStats', False):
    sys.stderr.write('\n')
    baseline = baselineStats.average()
    print indentText("""Statistics on {channelDesc}:
      waveforms:  {nWaveforms}
      baseline:   {baseline:.4g} +/- {baselineError:.4g}  (RMS: {baselineRMS:.4g})
      peak:       {peak:.4g} +/- {peakError:.4g}
      range:      {minVsBaseline:.4g} -- {maxVsBaseline:.4g}
    """.format(
      channelDesc=graphTitle,
      nWaveforms=nWaveforms,
      baseline=baseline,
      baselineError=baselineStats.RMS(),
      baselineRMS=baselineRMSstats.average(),
      peak=peakStats.average(),
      peakError=peakStats.RMS(),
      minVsBaseline=(Vrange.min() - baseline),
      maxVsBaseline=(Vrange.max() - baseline),
      ),
      indent="  ", firstIndent="", suppressIndentation=True,
    )

  return mgraph, sourcePaths
  
# plotSingleChannel()


def plotAllPositionWaveforms(sourceSpecs, canvasName = None, canvas = None, options = {}):
  
  timers = options.get('timers', WatchCollection(title="`plotAllPositionWaveforms()`: timings"))
  
  sourceSpecs = sourceSpecs.copy() # don't mess with the input argument
  fileList = []
  
  with timers.setdefault('total', description="total plot time"):
    sourceInfo = sourceSpecs.sourceInfo
    
    baseColors = Renderer.baseColors()
    
    channelRange = ExtremeAccumulator()
    
    # prepare a canvas to draw in, and split it
    if canvasName is None:
      canvasName = sourceInfo.formatString \
        ("C%(test)sWaves_Chimney%(chimney)s_Conn%(connection)s_Pos%(position)d")
    # if
    canvas = Renderer.makeWaveformCanvas \
      (canvasName, sourceInfo.MaxChannels, canvas=canvas, options=options)
    
    sys.stderr.write("Rendering:")
    # on each pad, draw a different channel info
    for channelIndex in xrange(1, sourceInfo.MaxChannels + 1):
      
      # each channel will have a multigraph with one graph for each waveform
      channelSourceSpecs = sourceSpecs.copy()
      channelSourceInfo = channelSourceSpecs.sourceInfo
      channelSourceInfo.setChannelIndex(channelIndex)
      channelRange.add(channelSourceInfo.channel)
      
      Renderer.selectPad(channelIndex - 1, canvas)
      
      channelInfo = plotSingleChannel(channelSourceSpecs, options=options)
      if not channelInfo:
        Renderer.SetRedBackgroundColor(canvas)
        continue # no graphs, bail out
      mgraph, channelFiles = channelInfo
      
      fileList.extend(channelFiles)
    # for channels
    
    Renderer.finalizeCanvas(
      canvas,
      title=(
        sourceInfo.formatString
          ("%(test)s waveforms from chimney %(chimney)s, connection %(connection)s")
        + ", channels %d-%d" % (channelRange.min(), channelRange.max())
      )
      )
    sys.stderr.write(" done.\n")
    return canvas, fileList
  # with total timer
# plotAllPositionWaveforms()


def plotSelectedChannelWaveforms(sourceSpecs, channels, canvasName = None, canvas = None, options = {}):
  
  timers = options.get('timers', WatchCollection(title="`plotSelectedChannelWaveforms()`: timings"))
  
  fileList = []
  sourceSpecs = sourceSpecs.copy() # don't mess with the input argument
  
  with timers.setdefault('total', description="total plot time"):
    sourceInfo = sourceSpecs.sourceInfo
    
    baseColors = Renderer.baseColors()
    
    # prepare a canvas to draw in, and split it
    if canvasName is None:
      try: channelsStr = channels.toString(fmt='02d')
      except AttributeError: channelsStr = str(channels)
      canvasName = sourceInfo.formatString \
       ("C%(test)sWaves_Chimney%(chimney)s_Conn%(connection)s_Channels" + channelsStr)
    # if
    
    canvas = Renderer.makeWaveformCanvas \
      (canvasName, len(channels), canvas=canvas, options=options)
    
    sys.stderr.write("Rendering:")
    # on each pad, draw a different channel info
    for iChannel, channel in enumerate(channels):
      
      # each channel will have a multigraph with one graph for each waveform
      channelSourceSpecs = sourceSpecs.copy()
      channelSourceInfo = channelSourceSpecs.sourceInfo
      channelSourceInfo.setChannel(channel)
      
      Renderer.selectPad(iChannel, canvas)
      
      channelInfo = plotSingleChannel(channelSourceSpecs, options=options)
      if not channelInfo:
        Renderer.SetRedBackgroundColor(canvas)
        continue # no graphs, bail out
      
      mgraph, channelFiles = channelInfo
      fileList.extend(channelFiles)
      
    # for channels
    
    Renderer.finalizeCanvas(
      canvas,
      title=(
        sourceInfo.formatString
          ("%(test)s waveforms from chimney %(chimney)s, connection %(connection)s")
        + ", channels {}".format(channels)
      )
      )
    sys.stderr.write(" done.\n")
    return canvas, fileList,
  # with total timer
# plotSelectedChannelWaveforms()


def plotAllPositionsAroundFile(path, canvasName = None, canvas = None, options = {}):
  
  sourceSpecs = parseWaveformSource(path)
  print sourceSpecs.describe()
  
  return plotAllPositionWaveforms(sourceSpecs, canvasName=canvasName, canvas=canvas, options=options.get('draw', {}))
  
# plotAllPositionAroundFile()


def statAllPositionWaveforms(sourceSpecs):

  sourceInfo = sourceSpecs.sourceInfo
  final = {}

  for channelIndex in xrange(1, sourceInfo.MaxChannels + 1):
    
    # each channel will hve a multigraph with one graph for each waveform
    channelSourceInfo = sourceInfo.copy()
    channelSourceInfo.setChannelIndex(channelIndex)
    channel = channelSourceInfo.channel
    
    #
    # drawing all waveforms and collecting statistics
    #
    baselineStats = StatAccumulator()
    baselineRMSstats = StatAccumulator()
    maxStats = StatAccumulator()
    minStats = StatAccumulator()
    peakStats = StatAccumulator()
    dipStats = StatAccumulator()
    absPeakStats = StatAccumulator()
    Vrange = ExtremeAccumulator()
    
    iSource = 0
    sourcePaths = sourceSpecs.allChannelSources(channelIndex=channelIndex)
    for sourcePath in sourcePaths:
      wf = readWaveform(sourcePath)
      if not wf: continue
      stats = extractStatistics(wf[0], wf[1])
      # if stats['baseline']['status'] == 'peakTooLow':
      #   print >> sys.stderr, 'Chimney %s, connection %s, channel %02d has too low peak!' % ( channelSourceInfo.chimney, channelSourceInfo.connection, channel )
      # elif stats['baseline']['status'] == 'swappedPeaks':
      #   print >> sys.stderr, 'Chimney %s, connection %s, channel %02d has swapped peak!' % ( channelSourceInfo.chimney, channelSourceInfo.connection, channel )
      baselineStats.add(stats['baseline']['value'], w=stats['baseline']['error'])
      baselineRMSstats.add(stats['baseline']['RMS'])
      maxStats.add(stats['maximum']['value'])
      minStats.add(stats['minimum']['value'])
      peakStats.add(stats['peaks']['positive']['value'])
      dipStats.add(stats['peaks']['negative']['value'])
      absPeakStats.add(stats['peaks']['absolute']['value'])
      Vrange.add(stats['maximum']['value'])
      Vrange.add(stats['minimum']['value'])
      iSource += 1
    # for
    if iSource == 0: 
      continue # no graphs, bail out
    
    finalStats = {}
    finalStats['nWaveforms'] = iSource
    finalStats['baseline'] = { 'average': baselineStats.average(), 'RMS': baselineRMSstats.average() }
    finalStats['maximum'] = { 'average': maxStats.average(), 'error': maxStats.averageError() }
    finalStats['minimum'] = { 'average': minStats.average(), 'error': minStats.averageError() }
    finalStats['peak'] = { 'average': peakStats.average(), 'RMS': peakStats.RMS() }
    finalStats['dip'] = { 'average': dipStats.average(), 'RMS': dipStats.RMS() }
    finalStats['absPeak'] = { 'average': absPeakStats.average(), 'RMS': absPeakStats.RMS() }
    # print "channel = %d" % channel
    # print "waveforms = %d" % finalStats['nWaveforms']
    # print "baseline = %.3f V (RMS %.3f V)" % ( finalStats['baseline']['average'], finalStats['baseline']['RMS'] )
    # print "maximum = (%.3f #pm %.3f) V" % ( finalStats['maximum']['average'], finalStats['maximum']['error'] )
    # print "peak = %.3f V (RMS %.3f V)" % ( finalStats['absPeak']['average'], finalStats['absPeak']['RMS'] )
    final[channel] = finalStats

  return final

# statAllPositionWaveforms()


def statAllPositionAroundFile(path, options = {}):
    
  sourceSpecs = parseWaveformSource(path)
  print sourceSpecs.describe()
  
  stats = statAllPositionWaveforms(sourceSpecs)
  
  return stats

# statAllPositionAroundFile()


################################################################################
### Test main programs (run with `--help` for explanations)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def waveformDrawer(argv):
  
  import argparse
  
  parser = argparse.ArgumentParser \
    (description='Draws all the waveforms from a specified position.')
  parser.set_defaults(printFiles=None)
  parser.add_argument \
    ('--filename', '-f', type=str, help='one of the files with the waveform')
  parser.add_argument \
    ('--chimney', '-C', type=str, help='chimney of the data to print')
  parser.add_argument(
    '--connection', '--cable', '-c', type=str,
    help='cable of the data to be printed (e.g. "V12")'
    )
  parser.add_argument(
    '--channels', '--channel', type=str,
    help='channel specification (e.g. "1-32" for all channels in the cable)'
    )
  parser.add_argument(
    '--allchannels', action="store_true", 
    help='plot all channels in the specified cable'
    )
  parser.add_argument(
    '--position', '-p', type=int,
    help='test box switch position of the data to be printed'
    )
  parser.add_argument(
    '--test', '-t', type=str, default="",
    help='name of the test to be printed [%(default)s]',
    )
  parser.add_argument(
    '--sourcedir', '--dir', '-d', type=str,
    help='path where the data files this chimney are'
    )
  parser.add_argument(
    '--waveforms', '-N', type=int, default=10,
    help='number of waveforms per channel [%(default)d]'
    )
  parser.add_argument(
    '--scopechannel', '-s', type=int,
    help='oscilloscope channel'
    )
  parser.add_argument(
    '--index', '-i', type=int,
    help='index of the waveform at the given position',
    )
  parser.add_argument('--render', '-R', type=str,
    choices=[ 'ROOT', 'matplotlib', 'none', ], default='ROOT',
    help='render system to be used [%(default)s]',
    )
  parser.add_argument(
    '--windowname', type=str,
    help='name of the window being drawn'
    )
  parser.add_argument(
    '--chimneystyle', type=str,
    choices=[ cls.Name for cls in ChimneyInfo.ValidStyles ],
    help="select a different style of chimney name for file lookup"
    )
  parser.add_argument("--saveas", action="append", default=[], type=str,
    help="formats to save a picture of the plots in"
    )
  parser.add_argument("--pause", "-P", action="store_true",
    help="waits for user input after drawing the waveforms")
  parser.add_argument("--timing", "-T", action="store_true",
    help="prints some profiling information")
  parser.add_argument("--stats", "-S", action="store_true",
    help="prints statistics on each channel")
  parser.add_argument("--files", "-F", action="store_true", dest='printFiles',
    help="prints name of each plotted source [only if `stats` not specified]")
  parser.add_argument("--nofiles", action="store_false", dest='printFiles',
    help="do not print the name of each plotted source")
  
  args = parser.parse_args(args=argv[1:])
  
  if args.printFiles is None: # default: 
    args.printFiles = not args.stats
  
  if args.filename:
    if args.chimney:
      logging.error("File name specified: chimney argument IGNORED.")
    if args.connection:
      logging.error("File name specified: connection argument IGNORED.")
    if args.position:
      logging.error("File name specified: position argument IGNORED.")
    if args.channels:
      logging.error("File name specified: channel argument IGNORED.")
    if args.test:
      logging.error("File name specified: test argument IGNORED.")
  else:
    if args.chimney is None:
      raise RuntimeError \
        ("Chimney argument is REQUIRED (unless filename is specified).")
    if args.connection is None:
      raise RuntimeError \
        ("Connection argument is REQUIRED (unless filename is specified).")
    if args.position is None and args.channels is None and not args.allchannels:
      raise RuntimeError \
        ("Position argument is REQUIRED (unless filename is specified).")
    
    if args.allchannels:
      if args.channels is not None:
        raise RuntimeError \
          ("Options `--channels` and `--allchannels` are mutually exclusive.")
      args.channels = '{}-{}'.format(1, WaveformSourceInfo.TotalChannels)
    # if all channels
        
    if args.channels is None:
      if args.scopechannel is None: args.scopechannel = 1
    else:
      if args.position is not None:
        raise RuntimeError \
          ("Options `channel` and `position` are mutually exclusive.")
      if args.scopechannel is not None:
        raise RuntimeError \
          ("Options `channel` and `scopechannel` are mutually exclusive.")
      args.channels = SelectedRange(args.channels)
    # if ... else

  #
  
  if args.chimneystyle:
    args.chimney = ChimneyInfo.convertToStyle(args.chimneystyle, args.chimney)
  
  useRenderer(args.render)
  
  options = {
    'timers': WatchCollection(title="Timings"),
    'printStats': args.stats,
    'N': args.waveforms,
  }
  
  if args.channels is not None:
    
    # we walk a tricky path here where channel, channel index and index are not
    # defined
    sourceInfo = WaveformSourceInfo(
      chimney=args.chimney,
      connection=args.connection,
      testName=args.test,
      )
    if args.sourcedir is None:
      args.sourcedir \
        = sourceInfo.formatString(WaveformSourceFilePath.StandardDirectory)
    # if
    
    sourceSpecs = WaveformSourceFilePath(sourceInfo, sourceDir=args.sourcedir)
    
    canvas, allFiles = plotSelectedChannelWaveforms \
     (sourceSpecs, args.channels, canvasName=args.windowname, options=options)
    del canvas
  else:
    if args.filename:
      sourceSpecs = parseWaveformSource(args.filename)
    else:
      # figure out the name from the information provided
      sourceInfo = WaveformSourceInfo(
        chimney=args.chimney,
        connection=args.connection,
        channelIndex=args.scopechannel,
        position=args.position,
        index=args.index,
        testName=args.test,
        )
      if args.index is None: sourceInfo.setFirstIndex(N=args.waveforms)
      if args.sourcedir is None:
        args.sourcedir \
          = sourceInfo.formatString(WaveformSourceFilePath.StandardDirectory)
      # if
      
      sourceSpecs = WaveformSourceFilePath(sourceInfo, sourceDir=args.sourcedir)
    #
    
    logging.info(sourceSpecs.describe())
    
    plotAllPositionWaveforms \
      (sourceSpecs, canvasName=args.windowname, options=options)
    
    allFiles = sourceSpecs.allPositionSources()
    
  # if
  
  if args.saveas: Renderer.saveCanvasAs(*args.saveas)
  
  if args.printFiles:
    print "Matching files:"
    for filePath in allFiles:
      print filePath,
      if not os.path.isfile(filePath): print " (NOT FOUND)",
      print
    # for
  # if print source files
    
  if args.timing:
    print options['timers'].toString(unit="ms", options=('times', 'average'))
  
  if args.pause: Renderer.pause()
  elif Renderer: logging.info("Reminder: use `--pause` to stop after drawing.")
  
  return 0
# waveformDrawer()


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def chimneyConverter(argv):
  
  import argparse
  
  parser = argparse.ArgumentParser \
    (description='Converts chimney names across different conventions.')
  parser.add_argument(
    'chimneys', metavar='chimney', type=str, nargs="*",
    help="chimney identificators to be converted (read from input if none)"
    )
  parser.add_argument(
    '--output', '-o', type=str, default=ChimneyInfo.StandardStyle.Name,
    choices=[ cls.Name for cls in ChimneyInfo.ValidStyles ],
    help="select the output style [%(default)s]"
    )
  parser.add_argument(
    '--input', '-i', type=str,
    choices=[ cls.Name for cls in ChimneyInfo.ValidStyles ],
    help="select the input style (default: autodetect)"
    )
  parser.add_argument(
    '--stdin', '-I', action="store_true",
    help="reads chimney identificators from input"
    )
  parser.add_argument(
    '--verbose', '-v', action="store_true",
    help="output in the form `INPUT CHIMNEY -> OUTPUT CHIMNEY`"
    )
  
  args = parser.parse_args(args=argv[1:])
  
  if args.stdin and args.chimneys:
    raise RuntimeError(
      "Reading chimneys from standard input would ignore the ones on command line."
      )
  if args.stdin or not args.chimneys:
    chimneys = sys.stdin
  else:
    chimneys = args.chimneys
  # if stdin
  
  for chimney in chimneys:
    for inputChimney in chimney.split():
      inputChimney = inputChimney.strip()
      outputChimney = ChimneyInfo.convertToStyle \
        (args.output, inputChimney, srcStyle=args.input)
      if args.verbose:
        print "{} -> {}".format(inputChimney, outputChimney)
      else:
        print outputChimney
    # for words
  # for
  
  return 0
# chimneyConverter()


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def fileFormatConverter(argv):
  
  import argparse
  
  logging.getLogger().setLevel(logging.INFO)
  
  parser = argparse.ArgumentParser \
    (description='Converts format of waveform file.')
  parser.add_argument(
    'inputFile', nargs="+",
    help="file holding the waveform"
    )
  parser.add_argument(
    '--output', '-o', type=str, default=None,
    help="output file name [build from input]"
    )
  parser.add_argument(
    '--outputdir', '-D', type=str, default=None,
    help="directory to place output files into (must exist) [same as input]"
    )
  parser.add_argument(
    '--inputversion', '-I', dest='inputVersion', type=int, default=None,
    help="version of input file [autodetect]"
    )
  parser.add_argument(
    '--outputversion', '-O', dest='outputVersion', type=int,
    help="version of output file to be written"
    )
  parser.add_argument(
    '--tobinary', '-B', dest='outputVersion', action="store_const",
    const=DefaultBinaryVersion,
    help="writes into binary format (version {})".format(DefaultBinaryVersion)
    )
  parser.add_argument(
    '--totext', '-T', dest='outputVersion', action="store_const", const=0,
    help="writes into text format"
    )
  
  args = parser.parse_args(args=argv[1:])
  
  if (len(args.inputFile) > 1) and (args.output is not None):
    raise RuntimeError \
     ("Output file name can be specified only with a single input file.")
  # if
  
  for inputFile in args.inputFile:
    
    outputFile = args.output
    if outputFile is None:
      basename, inputExt = os.path.splitext(inputFile)
      if inputExt.lower() in [ '.csv', '.txt', ]: # input text file
        outputFile = basename + '.dat'
        if args.inputVersion is None: args.inputVersion = 0 # text
      elif inputExt.lower() in [ '.dat', ]: # binary
        outputFile = basename + '.txt'
      else:
        outputFile = basename + ('.txt' if args.outputVersion == 0 else '.dat')
    # if detect output file
    if args.outputdir:
      outputFile = os.path.join(args.outputdir, os.path.basename(outputFile))
    
    if outputFile == inputFile:
      # we could though...
      raise RuntimeError \
       ("Replacing a data file is not supported ('{}')".format(inputFile))
    #
    
    logging.info("'{inputFile}' => '{outputFile}'"
     .format(inputFile=inputFile, outputFile=outputFile)
     )
    
    t, V = readWaveformFile(inputFile, version=args.inputVersion)
    writeWaveformFile(t, V, outputFile, version=args.outputVersion)
    
  # for
  return 0
# fileFormatConverter()


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# main program dispatcher
#
if __name__ == "__main__":
  
  import sys, os
  
  mainPrograms = {
    'convertchimney': chimneyConverter,
    'convertfileformat': fileFormatConverter,
    None: waveformDrawer, # default
  }
  
  mainProgramKey = os.path.splitext(os.path.basename(sys.argv[0]))[0].lower()
  if mainProgramKey not in mainPrograms: mainProgramKey = None
  
  sys.exit(mainPrograms[mainProgramKey](sys.argv))
  
# main
