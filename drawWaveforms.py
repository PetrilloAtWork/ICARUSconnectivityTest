#!/usr/bin/env python

from stopwatch import WatchCollection
import sys
import os
import re
import math
import logging


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
  
  StandardStyle = AlphabeticStyle
  
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
  def convertToStyleAndSplit(style, chimney, srcStyle = None):
    if not issubclass(style, ChimneyInfo.StyleBase):
      styleName = style
      style = ChimneyInfo.findStyle(styleName)
      if style is None:
        raise RunetimeError("Chimney name style '{}' invalid".format(styleName))
    # if style is name
    if not srcStyle: # autodetect original style
      srcStyle, info = ChimneyInfo.styleMatcher(chimney)
      if srcStyle is ChimneyInfo.InvalidStyle:
        raise RuntimeError("'{}' is not a valid chimney.".format(chimney))
      row, number = info
    else:
      row, number = srcStyle.split(chimney)
    #
    if srcStyle is not style:
      row, number = srcStyle.toStandard(row, number)
      row, numner = style.fromStandard(row, number)
    return (row, number)
  # convertToStyleAndSplit()
  
  @staticmethod
  def convertToStyle(style, chimney, srcStyle = None):
    return style.format_ \
      (ChimneyInfo.convertToStyleAndSplit(style, chimney, srcStyle=srcStyle))
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
  
  Pattern = re.compile('[A-Z][0-9]{1,2}')
  
  @staticmethod
  def isCable(cable):
    return CableInfo.Pattern.match(cable.upper()) is not None
  
# class CableInfo



class WaveformSourceInfo:
  
  MaxChannels = 4
  
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
  # __init__()
  
  def copy(self):
    return WaveformSourceInfo(
      chimney=self.chimney, connection=self.connection,
      channelIndex=self.channelIndex, position=self.position,
      index=self.index, testName=self.test,
      )
  # copy()
  
  def formatString(self, s): return s % vars(self)
  
  def setChannelIndex(self, channelIndex):
    self.channelIndex = channelIndex
    self.updateChannel()
  def setPosition(self, position):
    self.position = position
    self.updateChannel()
  def setIndex(self, index): self.index = index
  def setFirstIndex(self, N = 10):
    self.setIndex(self.firstIndexOf(self.position, N=N))
  def increaseIndex(self, amount = 1): self.index += amount
  
  def updateChannel(self):
    self.channel = \
      None if self.position is None or self.channelIndex is None \
      else (self.position - 1) * WaveformSourceInfo.MaxChannels + self.channelIndex
  # updateChannel()
  
  @staticmethod
  def firstIndexOf(position, N = 10): return (position - 1) * N + 1
  
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
  
  def allChannelSources(self, channelIndex = None, N = 10):
    """Returns the list of N expected waveform files at the specified channel index."""
    values = self.sourceInfo.copy()
    if channelIndex is not None: values.setChannelIndex(channelIndex)
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
    for channelIndex in xrange(1, WaveformSourceInfo.MaxChannels + 1): files.extend(self.allChannelSources(channelIndex, N))
    return files
  # allPositionSources()
  
# class WaveformSourceFilePath


def parseWaveformSource(path):
  """Parses `path` and returns a filled `WaveformSourceFilePath`.
  
  The expected pattern is:
  
  "path/waveform_CH3_CHIMNEY_EE11_CONN_V12_POS_7_62.csv"
  
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
      try: sourceInfo.chimney = tokens[iToken]
      except IndexError:
        raise RuntimeError("Error parsing file name '%s': no chimney." % triggerFileName)
      iToken += 1
      sourceFilePattern.extend([ Token, "%(chimney)s", ])
      continue
    elif TOKEN == 'CONN':
      try: sourceInfo.connection = tokens[iToken]
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
    return self.average() / math.sqrt(self.w)
  def RMS(self):
    return math.sqrt(max(self.wx2 / self.w - self.average()**2, 0.0))
  def averageSquares(self):
    return self.wx2 / self.w
  
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


def extractBaselineFromPedestal(t, V, iPeak):
  margin = int(0.1 * len(V)) # 10% of the full range
  
  iEnd = iPeak - margin
  if iEnd < 10:
    # we should bail out here; as a workaround, instead, we get the baseline anyway
    # raise RuntimeError("Peak (at #%d) too close to the start of the waveform, can't extract pedestal." % iPeak)
    iEnd = margin
  
  stats = StatAccumulator()
  for i in xrange(iEnd): stats.add(V[i])
  
  return {
    'value': stats.average(), 'error': stats.averageError(), 'RMS': stats.RMS(),
    }
  
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


def extractPeaks(t, V, baseline):
  """A barely acceptable algorithm to find peaks w.r.t. waveform baseline.
  
  Quite shameful.
  """
  
  iMin, iMax = findExtremes(t, V)
  return {
    'positive': { 'value': V[iMax] - baseline, 'valueError': 0.0, 'time': t[iMax], 'timeError': 0.0, },
    'negative': { 'value': V[iMin] - baseline, 'valueError': 0.0, 'time': t[iMin], 'timeError': 0.0, },
    }
# extractPeaks()


def extractStatistics(t, V):
  stats = {}
  
  iMax = findMaximum(t, V)
  stats['maximum'] = { 'value': V[iMax], 'time': t[iMax], 'pos': iMax, }
  
  iMin = findMinimum(t, V)
  stats['minimum'] = { 'value': V[iMin], 'time': t[iMin], 'pos': iMin, }
  
  stats['baseline'] = extractBaseline(t, V)
  
  stats['peaks'] = extractPeaks(t, V, stats['baseline']['value'])
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
  
  def plotFromFile(self, filePath): return None
  
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
  
  def pause(self):
    print "Press <Enter> to continue."
    sys.stdin.readline()
  # pause()
  
# class VirtualRenderer

################################################################################
class NullRenderer(VirtualRenderer): pass

################################################################################
class MPLRendering:
  
  def __init__(self):
    raise NotImplementedError("matplotlib rendering has not been implemented yet")
  
  def makeWaveformCanvas(self, canvasName, nPads, options = {}, canvas = None):
    return None
  
  def selectPad(self, iPad, canvas = None): pass
  
  def plotFromFile(self, filePath): return None
  
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
    return self.ROOT.TGraph(filePath, '%lg,%lg')
  
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
  
  @staticmethod
  def baseColors():
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
    return None
  graph = Renderer.plotFromFile(filePath)
  logging.debug("'{file}': {points} points"
    .format(file=filePath, points= Renderer.graphPoints(graph))
    )
  graphName = sourceInfo.formatString("GWaves%(chimney)s_Conn%(connection)s_Ch%(channel)d_I%(index)d")
  graphTitle = sourceInfo.formatString("Chimney %(chimney)s connection %(connection)s channel %(channel)d (%(index)d)")
  Renderer.setObjectNameTitle(graph, graphName, graphTitle)
  return graph
  
# plotWaveformFromFile()


def plotAllPositionWaveforms(sourceSpecs, canvasName = None, canvas = None, options = {}):
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
  
  with timers.setdefault('total', description="total plot time"):
    sourceInfo = sourceSpecs.sourceInfo
    
    baseColors = Renderer.baseColors()
    
    channelRange = ExtremeAccumulator()
    
    # prepare a canvas to draw in, and split it
    if canvasName is None:
      canvasName = sourceInfo.formatString \
        ("C%(test)sWaves%(chimney)s_Conn%(connection)s_Pos%(position)d")
    # if
    canvas = Renderer.makeWaveformCanvas \
      (canvasName, sourceInfo.MaxChannels, canvas=canvas, options=options)
    
    sys.stderr.write("Rendering:")
    # on each pad, draw a different channel info
    for channelIndex in xrange(1, sourceInfo.MaxChannels + 1):
      
      sys.stderr.write(" CH{:d}".format(channelIndex))
      
      with timers.setdefault('channel', description="channel plot time"):
        # each channel will hve a multigraph with one graph for each waveform
        channelSourceInfo = sourceInfo.copy()
        channelSourceInfo.setChannelIndex(channelIndex)
        
        Renderer.selectPad(channelIndex - 1, canvas)
        channelRange.add(channelSourceInfo.channel)
        
        baseColor = baseColors[channelIndex % len(baseColors)]
        
        graphName = channelSourceInfo.formatString \
          ("MG_%(chimney)s_%(connection)s_POS%(position)d_CH%(channelIndex)d")
        mgraph = Renderer.makeMultiplot(
         name=graphName,
         title=channelSourceInfo.formatString
          ("Chimney %(chimney)s connection %(connection)s channel %(channel)s")
         )
        
        #
        # drawing all waveforms and collecting statistics
        #
        baselineStats = StatAccumulator()
        baselineRMSstats = StatAccumulator()
        maxStats = StatAccumulator()
        peakStats = StatAccumulator()
        Vrange = ExtremeAccumulator()
        
        iSource = 0
        sourcePaths = sourceSpecs.allChannelSources(channelIndex)
        for sourcePath in sourcePaths:
          with timers.setdefault('graph', description="graph creation"):
            graph = plotWaveformFromFile(sourcePath, sourceInfo=channelSourceInfo)
            if not graph: continue
            Renderer.addPlotToMultiplot(graph, mgraph, baseColor)
          # with graph timer
          
          with timers.setdefault('stats', description="statistics extraction"):
            stats = extractStatistics(graph.GetX(), graph.GetY())
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
        if iSource == 0:
          Renderer.SetRedBackgroundColor(canvas)
          continue # no graphs, bail out
        
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
            "waveforms = %d" % iSource,
            "baseline = %.3f V (RMS %.3f V)" % (baselineStats.average(), baselineRMSstats.average()),
            "maximum = (%.3f #pm %.3f) V" % (maxStats.average(), maxStats.averageError()),
            "peak = %.3f V (RMS %.3f V)" % (peakStats.average(), peakStats.RMS())
            ]
          Renderer.drawLegendOnCanvas(statsText, graphName + "_stats")
        # with drawstats timer
        
      # with channel timer
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
    return canvas
  # with total timer
# plotAllPositionWaveforms()


def plotAllPositionsAroundFile(path, canvasName = None, canvas = None, options = {}):
  
  sourceSpecs = parseWaveformSource(path)
  print sourceSpecs.describe()
  
  return plotAllPositionWaveforms(sourceSpecs, canvasName=canvasName, canvas=canvas, options=options.get('draw', {}))
  
# plotAllPositionAroundFile()


################################################################################
### Test main program (run with `--help` for explanations)

if __name__ == "__main__":
  
  import argparse
  
  parser = argparse.ArgumentParser \
    (description='Draws all the waveforms from a specified position.')
  parser.add_argument \
    ('--filename', '-f', type=str, help='one of the files with the waveform')
  parser.add_argument \
    ('--chimney', '-C', type=str, help='chimney of the data to print')
  parser.add_argument(
    '--connection', '--cable', '-c', type=str,
    help='cable of the data to be printed (e.g. "V12")'
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
    choices=[ 'ROOT', 'matplotlib', ], default='ROOT',
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
  
  args = parser.parse_args()
  
  if args.filename:
    if args.chimney:
      logging.error("File name specified: chimney argument IGNORED.")
    if args.connection:
      logging.error("File name specified: connection argument IGNORED.")
    if args.position:
      logging.error("File name specified: position argument IGNORED.")
    if args.test:
      logging.error("File name specified: test argument IGNORED.")
  else:
    if args.chimney is None:
      raise RuntimeError \
        ("Chimney argument is REQUIRED (unless filename is specified.")
    if args.connection is None:
      raise RuntimeError \
        ("Connection argument is REQUIRED (unless filename is specified.")
    if args.position is None:
      raise RuntimeError \
        ("Position argument is REQUIRED (unless filename is specified.")
    if args.scopechannel is None:
      args.scopechannel = 1
  #
  
  if args.chimneystyle:
    args.chimney = ChimneyInfo.convertToStyle(args.chimneystyle, args.chimney)
  
  useRenderer(args.render)
  
  if args.filename:
    sourceSpecs = parseWaveformSource(args.filename)
  else:
    # figure out the name from the information provided
    if args.sourcedir is None: args.sourcedir = "CHIMNEY_" + str(args.chimney)
    
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
  
  plotAllPositionWaveforms(sourceSpecs, canvasName=args.windowname)
  
  if isinstance(Renderer, ROOTrendering):
    for format_ in args.saveas:
      ROOT.gPad.SaveAs(ROOT.gPad.GetName() + "." + format_)
  # if ROOT
  
  allFiles = sourceSpecs.allPositionSources()
  print "Matching files:"
  for filePath in allFiles:
    print filePath,
    if not os.path.isfile(filePath): print " (NOT FOUND)",
    print
  # for
  
  if args.pause: Renderer.pause()
  elif Renderer: logging.info("Reminder: use `--pause` to stop after drawing.")
  
# main
