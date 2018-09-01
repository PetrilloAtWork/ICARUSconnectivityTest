#!/usr/bin/env python

import sys
import os
import re

try:
  import ROOT
  hasROOT = True
except ImportError:
  print >>sys.stderr, "Unable to set ROOT up. Some features will be missing."
  hasROOT = False


class MinMax:
  
  def __init__(self):
    self.min = None
    self.max = None
  def add(self, value):
    if self.min is None or value < self.min: self.min = value
    if self.max is None or value > self.max: self.max = value
  
# class MinMax


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
  def increaseIndex(self, amount = 1): self.index += amount
  
  def updateChannel(self):
    self.channel = \
      None if self.position is None or self.channelIndex is None \
      else (self.position - 1) * WaveformSourceInfo.MaxChannels + self.channelIndex
  # updateChannel()
  
  @staticmethod
  def firstIndexOf(position, N = 10): return (position - 1) * N + 1
  
# class WaveformSourceInfo


class WaveformSourceParser:
  
  def __init__(self, path = None):
    if path is not None: self.parse(path)
  
  def setup(self, chimney, connection, position, channelIndex, index, filePattern, sourceDir = ".", ):
    """
    The expected pattern is:
    
    "path/waveform_CH3_CHIMNEY_EE11_CONN_V12_POS_7_62.csv"
    
    """
    self.sourceDir = sourceDir
    self.sourceFilePattern = filePattern
    self.sourceInfo = WaveformSourceInfo(
      chimney=chimney, connection=connection, position=position,
      channelIndex=channelIndex, index=index
      )
    
    self.sourceInfo.updateChannel()
    self.sourceFilePattern = filePattern
  # setup()
  
  def parse(self, path):
    """
    The expected pattern is:
    
    "path/waveform_CH3_CHIMNEY_EE11_CONN_V12_POS_7_62.csv"
    
    """
    self.sourceDir, self.triggerFileName = os.path.split(path)
    
    name, ext = os.path.splitext(self.triggerFileName)
    if ext.lower() != '.csv':
      print >>sys.stderr, "Warning: the file '%s' has not the name of a comma-separated values file (CSV)." % path
    tokens = name.split("_")
    
    self.sourceInfo = WaveformSourceInfo()
    
    self.sourceFilePattern = []
    
    iToken = 0
    while iToken < len(tokens):
      Token = tokens[iToken]
      iToken += 1
      TOKEN = Token.upper()
      
      if TOKEN == 'CHIMNEY':
        try: self.sourceInfo.chimney = tokens[iToken]
        except IndexError:
          raise RuntimeError("Error parsing file name '%s': no chimney." % self.triggerFileName)
        iToken += 1
        self.sourceFilePattern.extend([ Token, "%(chimney)s", ])
        continue
      elif TOKEN == 'CONN':
        try: self.sourceInfo.connection = tokens[iToken]
        except IndexError:
          raise RuntimeError("Error parsing file name '%s': no connection code." % self.triggerFileName)
        iToken += 1
        self.sourceFilePattern.extend([ Token, "%(connection)s", ])
        continue
      elif TOKEN == 'POS':
        try: self.sourceInfo.position = int(tokens[iToken])
        except IndexError:
          raise RuntimeError("Error parsing file name '%s': no connection code." % self.triggerFileName)
        except ValueError:
          raise RuntimeError("Error parsing file name '%s': '%s' is not a valid position." % (self.triggerFileName, tokens[iToken]))
        self.sourceFilePattern.extend([ Token, "%(position)s", ])
        iToken += 1
        continue
      elif TOKEN == 'WAVEFORM':
        channel = tokens[iToken]
        if not channel.startswith('CH'):
          raise RuntimeError("Error parsing file name '%s': '%s' is not a valid channel." % (self.triggerFileName, channel))
        try: self.sourceInfo.setChannelIndex(int(channel[2:]))
        except IndexError:
          raise RuntimeError("Error parsing file name '%s': no connection code." % self.triggerFileName)
        except ValueError:
          raise RuntimeError("Error parsing file name '%s': '%s' is not a valid channel number." % (self.triggerFileName, channel[2:]))
        self.sourceFilePattern.extend([ Token, "CH%(channelIndex)d", ])
        iToken += 1
        continue
      else:
        try:
          self.sourceInfo.setIndex(int(Token))
          self.sourceFilePattern.append('%(index)d')
        except ValueError:
          print >>sys.stderr, "Unexpected tag '%s' in file name '%s'" % (Token, self.triggerFileName)
          self.sourceFilePattern.append(Token)
      # if ... else
    # while
    
    if self.sourceInfo.chimney is None: raise RuntimeError("No chimney specified in file name '%s'" % self.triggerFileName)
    if self.sourceInfo.connection is None: raise RuntimeError("No connection specified in file name '%s'" % self.triggerFileName)
    if self.sourceInfo.position is None: raise RuntimeError("No position specified in file name '%s'" % self.triggerFileName)
    if self.sourceInfo.channelIndex is None: raise RuntimeError("No channel specified in file name '%s'" % self.triggerFileName)
    if self.sourceInfo.index is None: raise RuntimeError("No index specified in file name '%s'" % self.triggerFileName)
    
    self.sourceInfo.updateChannel()
    self.sourceFilePattern = "_".join(self.sourceFilePattern)
    if ext: self.sourceFilePattern += ext
    
  # parse()
  
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
  
  
# class WaveformSourceParser


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


def plotAllPositionWaveforms(sourceSpecs, canvasName = None, canvas = None):
  #
  # The `ROOT.SetOwnership()` calls free the specified ROOT objects from python
  # garbage collection scythe. We need that because since we created them,
  # we own them, and drawing them does not leave references behind that could
  # keep them around.
  #
  sourceInfo = sourceSpecs.sourceInfo
  
  # we support only groups of four channels
  nPadsX = 2;
  nPadsY = 2;
  assert sourceInfo.MaxChannels == nPadsX * nPadsY
  
  baseColors = ( ROOT.kBlack, ROOT.kYellow + 1, ROOT.kCyan, ROOT.kMagenta, ROOT.kGreen )
  
  channelRange = MinMax()
  
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
  canvas.Divide(nPadsX, nPadsY)
  canvas.cd()
  
  # on each pad, draw a different channel info
  for channelIndex in xrange(1, sourceInfo.MaxChannels + 1):
    
    # each channel will hve a multigraph with one graph for each waveform
    channelSourceInfo = sourceInfo.copy()
    channelSourceInfo.setChannelIndex(channelIndex)
    
    channelRange.add(channelSourceInfo.channel)
    
    pad = canvas.cd(channelIndex)
    pad.SetFillColor(ROOT.kWhite)
    pad.SetGridx()
    pad.SetGridy()
    
    sourcePaths = sourceSpecs.allChannelSources(channelIndex)
    
    baseColor = baseColors[channelIndex % len(baseColors)]
    
    mgraph = ROOT.TMultiGraph()
    mgraph.SetName(channelSourceInfo.formatString("MG_%(chimney)s_%(connection)s_POS%(position)d_CH%(channelIndex)d"))
    mgraph.SetTitle(channelSourceInfo.formatString("Chimney %(chimney)s connection %(connection)s channel %(channel)s"))
    
    iSource = 0
    for sourcePath in sourcePaths:
      graph = plotWaveformFromFile(sourcePath, sourceInfo=channelSourceInfo)
      if not graph: continue
      ROOT.SetOwnership(graph, False)
      graph.SetLineColor(baseColor)
      graph.Draw("AL")
      mgraph.Add(graph, "L")
      iSource += 1
    # for
    if iSource == 0: 
      pad.SetFillColor(ROOT.kRed)
      continue # no graphs, bail out
    ROOT.SetOwnership(mgraph, False)
    mgraph.Draw("A")
    xAxis = mgraph.GetXaxis()
    xAxis.SetDecimals()
    xAxis.SetTitle("time  [s]")
    yAxis = mgraph.GetYaxis()
    yAxis.SetDecimals()
    yAxis.SetTitle("signal  [V]")
  # for channels
  canvas.cd(0)
  
  canvas.SetTitle(sourceInfo.formatString("Waveforms from chimney %(chimney)s, connection %(connection)s") + ", channels %(min)d-%(max)d" % vars(channelRange))
  canvas.Draw()
  
  return canvas
# plotAllPositionWaveforms()


def plotAllPositionsAroundFile(path):
  
  sourceSpecs = WaveformSourceParser(path)
  print sourceSpecs.describe()
  
  plotAllPositionWaveforms(sourceSpecs)
  
# plotAllPositionAroundFile()


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
  
  plotAllPositionAroundFile(args.fileName)
  
  if ROOT.gPad: ROOT.gPad.SaveAs(ROOT.gPad.GetName() + ".pdf")
  
  AllFiles = WaveformSourceParser(args.fileName).allPositionSources()
  print "Matching files:"
  for filePath in AllFiles:
    print filePath,
    if not os.path.isfile(filePath): print " (NOT FOUND)",
    print
  # for
  
# main
