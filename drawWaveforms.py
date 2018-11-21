#!/usr/bin/env python

import sys
import os
import re
import math

try:
  import ROOT
  hasROOT = True
except ImportError:
  print >>sys.stderr, "Unable to set ROOT up. Some features will be missing."
  hasROOT = False


################################################################################
### WaveformSourceInfo: data structure with waveform identification parameters

class WaveformSourceInfo:
  
  MaxChannels = 4
  
  def __init__(self,
   chimney=None, connection=None, channelIndex=None, position=None,
   index=None
   ):
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
      index=self.index
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
  StandardPattern = "waveform_CH%(channelIndex)d_CHIMNEY_%(chimney)s_CONN_%(connection)s_POS_%(position)d_%(index)d.csv"
  
  def __init__(self, sourceInfo, filePattern, sourceDir = "."):
    """
    The expected pattern is:
    
    "path/waveform_CH3_CHIMNEY_EE11_CONN_V12_POS_7_62.csv"
    
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
  
  def allChannelSources(self, channelIndex, N = 10):
    values = self.sourceInfo.copy()
    values.setChannelIndex(channelIndex)
    values.setIndex((self.sourceInfo.position - 1) * N)
    
    files = []
    for i in xrange(N):
      values.increaseIndex()
      files.append(os.path.join(self.sourceDir, self.sourceFilePattern % vars(values)))
    # for i
    return files
  # allChannelSources()
  
  def allPositionSources(self, N = 10):
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
    elif TOKEN == 'WAVEFORM':
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
  
  return WaveformSourceFilePath(
    chimney,
    connection,
    position,
    channelIndex,
    index,
    filePattern,
    sourceDir
    )
  
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
  """A barely acceptable algorithm t find peaks w.r.t. waveform baseline.
  
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

def plotWaveformFromFile(filePath, sourceInfo = None):
  
  if not os.path.exists(filePath):
    print >>sys.stderr, "Can't plot data from '%s': file not found." % (filePath)
    return None
  graph = ROOT.TGraph(filePath, '%lg,%lg')
  print "'%s': %d points" % (filePath, graph.GetN())
  graphName = sourceInfo.formatString("GWaves%(chimney)s_Conn%(connection)s_Ch%(channel)d_I%(index)d")
  graphTitle = sourceInfo.formatString("Chimney %(chimney)s connection %(connection)s channel %(channel)d (%(index)d)")
  graph.SetNameTitle(graphName, graphTitle)
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

  sourceInfo = sourceSpecs.sourceInfo
  
  baseColors = ( ROOT.kBlack, ROOT.kYellow + 1, ROOT.kCyan + 1, ROOT.kMagenta + 1, ROOT.kGreen + 1)
  
  channelRange = ExtremeAccumulator()
  
  # prepare a canvas to draw in, and split it
  if canvasName is None:
    canvasName = sourceInfo.formatString("CWaves%(chimney)s_Conn%(connection)s_Pos%(position)d")
  if canvas is None:
    canvas = ROOT.TCanvas(canvasName, canvasName)
  else:
    canvas.cd()
    canvas.Clear()
    canvas.SetName(canvasName)
  ROOT.SetOwnership(canvas, False)
  if options.get("grid", "square").lower() in [ "square", "default", ]:
    canvas.DivideSquare(sourceInfo.MaxChannels)
  elif options["grid"].lower() == "vertical":
    canvas.Divide(1, sourceInfo.MaxChannels)
  elif options["grid"].lower() == "horizontal":
    canvas.Divide(sourceInfo.MaxChannels, 1)
  else:
    raise RuntimeError("Option 'grid' has unrecognised value '%s'" % options['grid'])
  canvas.cd()
  
  # on each pad, draw a different channel info
  for channelIndex in xrange(1, sourceInfo.MaxChannels + 1):
    
    # each channel will hve a multigraph with one graph for each waveform
    channelSourceInfo = sourceInfo.copy()
    channelSourceInfo.setChannelIndex(channelIndex)
    
    channelRange.add(channelSourceInfo.channel)
    
    #
    # pad graphic options preparation
    #
    pad = canvas.cd(channelIndex)
    pad.SetFillColor(ROOT.kWhite)
    pad.SetLeftMargin(0.08)
    pad.SetRightMargin(0.03)
    pad.SetBottomMargin(0.06)
    pad.SetGridx()
    pad.SetGridy()
    
    baseColor = baseColors[channelIndex % len(baseColors)]
    
    mgraph = ROOT.TMultiGraph()
    mgraph.SetName(channelSourceInfo.formatString("MG_%(chimney)s_%(connection)s_POS%(position)d_CH%(channelIndex)d"))
    mgraph.SetTitle(channelSourceInfo.formatString("Chimney %(chimney)s connection %(connection)s channel %(channel)s"))
    
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
      graph = plotWaveformFromFile(sourcePath, sourceInfo=channelSourceInfo)
      if not graph: continue
      ROOT.SetOwnership(graph, False)
      graph.SetLineColor(baseColor)
      
      stats = extractStatistics(graph.GetX(), graph.GetY())
      baselineStats.add(stats['baseline']['value'], w=stats['baseline']['error'])
      baselineRMSstats.add(stats['baseline']['RMS'])
      maxStats.add(stats['maximum']['value'])
      peakStats.add(stats['peaks']['absolute']['value'])
      Vrange.add(stats['maximum']['value'])
      Vrange.add(stats['minimum']['value'])
      
      mgraph.Add(graph, "L")
      iSource += 1
    # for
    if iSource == 0: 
      pad.SetFillColor(ROOT.kRed)
      continue # no graphs, bail out
    
    ROOT.SetOwnership(mgraph, False)
    mgraph.Draw("A")
    
    #
    # setting (multi)graph graphic options
    #
    xAxis = mgraph.GetXaxis()
    xAxis.SetDecimals()
    xAxis.SetTitle("time  [s]")
    # set the range to a minimum
    yAxis = mgraph.GetYaxis()
    yAxis.SetDecimals()
    yAxis.SetTitle("signal  [V]")
    # instead of hard-coding the expected baseline of ~2.0 we use the actual
    # baseline average, rounded at 100 mV (one decimal digit)
    drawBaseline = round(baselineStats.average(), 1)
    Ymin = drawBaseline - defYamplitude
    Ymax = drawBaseline + defYamplitude
    if (Vrange.min() >= Ymin and Vrange.max() <= Ymax):
      yAxis.SetRangeUser(Ymin - defYmargin, Ymax + defYmargin)
    
    #
    # statistics box
    #
    statsText = [
      "waveforms = %d" % iSource,
      "baseline = %.3f V (RMS %.3f V)" % (baselineStats.average(), baselineRMSstats.average()),
      "maximum = (%.3f #pm %.3f) V" % (maxStats.average(), maxStats.averageError()),
      "peak = %.3f V (RMS %.3f V)" % (peakStats.average(), peakStats.RMS())
      ]
    # "none" is a hack: `TPaveText` deals with NDC and removes it from the options,
    # then passes the options to `TPave`; if `TPave` finds an empty option string
    # (as it does when the original option was just "NDC"), it sets a "br" default;
    # but ROOT does not punish the presence of unsupported options.
    statBox = ROOT.TPaveStats(0.60, 0.80 - 0.025*len(statsText), 0.98, 0.92, "NDC none")
    statBox.SetOptStat(0); # do not print title (the other flags are ignored)
    statBox.SetBorderSize(1)
    statBox.SetName(mgraph.GetName() + "_stats")
    for statText in statsText: statBox.AddText(statText)
    statBox.SetFillColor(ROOT.kWhite)
    statBox.SetTextFont(42) # regular (not bold) sans serif, scalable
    statBox.Draw()
    ROOT.SetOwnership(statBox, False)
    
  # for channels
  canvas.cd(0)
  
  canvas.SetTitle(sourceInfo.formatString("Waveforms from chimney %(chimney)s, connection %(connection)s") + ", channels %d-%d" % (channelRange.min(), channelRange.max()))
  canvas.Draw()
  
  return canvas
# plotAllPositionWaveforms()


def plotAllPositionsAroundFile(path, canvasName = None, canvas = None, options = {}):
  
  sourceSpecs = parseWaveformSource(path)
  print sourceSpecs.describe()
  
  return plotAllPositionWaveforms(sourceSpecs, canvasName=canvasName, canvas=canvas, options=options.get('draw', {}))
  
# plotAllPositionAroundFile()


################################################################################
### Test main program (run with `--help` for explanations)
"""
import ROOT
from drawWaveforms import plotAllPositionAroundFile
plotAllPositionAroundFile("/Users/petrillo/Desktop/Scope_71/CHIMNEY_EE11/waveform_CH4_CHIMNEY_EE11_CONN_V06_POS_8_80.csv")
"""

if __name__ == "__main__":
  
  import argparse
  
  parser = argparse.ArgumentParser \
    (description='Draws all the waveforms from a specified position.')
  parser.add_argument \
    ('fileName', type=str, help='one of the files with the waveform')
  
  args = parser.parse_args()
  
  plotAllPositionsAroundFile(args.fileName)
  
  if ROOT.gPad: ROOT.gPad.SaveAs(ROOT.gPad.GetName() + ".pdf")
  
  AllFiles = parseWaveformSource(args.fileName).allPositionSources()
  print "Matching files:"
  for filePath in AllFiles:
    print filePath,
    if not os.path.isfile(filePath): print " (NOT FOUND)",
    print
  # for
  
# main