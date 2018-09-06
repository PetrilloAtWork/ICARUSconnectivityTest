#!/usr/bin/env python

import sys
import os
import glob
import ROOT
import drawWaveforms

## A C/C++ structure is required, to allow memory based access
ROOT.gROOT.ProcessLine(
"struct treeVars_t {\
  Char_t  chimney[5];\
  Int_t   connection;\
  Int_t   channel;\
  Int_t   nWaveforms;\
  Float_t peak;\
  Float_t peakErr;\
  Float_t dip;\
  Float_t dipErr;\
  Float_t absPeak;\
  Float_t absPeakErr;\
  Float_t baseline;\
  Float_t rms;\
  Float_t maximum;\
  Float_t maximumErr;\
  Float_t minimum;\
  Float_t minimumErr;\
};" );
# gROOT.ProcessLine


def createOutROOTFile( outFile ):
  # f = ROOT.TFile( outFile, "UPDATE" )
  f = ROOT.TFile( outFile, "RECREATE" )


  if not f:
    print >> sys.stderr, "Cannot open %s" % outFile
    sys.exit( 1 )

  return f

# createOutROOTFile()

def accessTTree():

  treeVars = ROOT.treeVars_t()
  
  tree = ROOT.TTree( 'ConnectivityAna', 'Analysis TTree of the connectivity test' )
  tree.Branch( 'Chimney', ROOT.AddressOf( treeVars, 'chimney' ), 'Chimney/C' )
  tree.Branch( 'Connection', ROOT.AddressOf( treeVars, 'connection' ), 'Connection/I' )
  tree.Branch( 'Channel', ROOT.AddressOf( treeVars, 'channel' ), 'Channel/I' )
  tree.Branch( 'nWaveforms', ROOT.AddressOf( treeVars, 'nWaveforms' ), 'nWaveforms/I' )
  tree.Branch( 'Peak', ROOT.AddressOf( treeVars, 'peak' ), 'Peak/F' )
  tree.Branch( 'PeakErr', ROOT.AddressOf( treeVars, 'peakErr' ), 'PeakErr/F' )
  tree.Branch( 'Dip', ROOT.AddressOf( treeVars, 'dip' ), 'Dip/F' )
  tree.Branch( 'DipErr', ROOT.AddressOf( treeVars, 'dipErr' ), 'DipErr/F' )
  tree.Branch( 'AbsPeak', ROOT.AddressOf( treeVars, 'absPeak' ), 'AbsPeak/F' )
  tree.Branch( 'AbsPeakErr', ROOT.AddressOf( treeVars, 'absPeakErr' ), 'AbsPeakErr/F' )
  tree.Branch( 'Baseline', ROOT.AddressOf( treeVars, 'baseline' ), 'Baseline/F' )
  tree.Branch( 'RMS', ROOT.AddressOf( treeVars, 'rms' ), 'RMS/F' )
  tree.Branch( 'Maximum', ROOT.AddressOf( treeVars, 'maximum' ), 'Maximum/F' )
  tree.Branch( 'MaximumErr', ROOT.AddressOf( treeVars, 'maximumErr' ), 'MaximumErr/F' )
  tree.Branch( 'Minimum', ROOT.AddressOf( treeVars, 'minimum' ), 'Minimum/F' )
  tree.Branch( 'MinimumErr', ROOT.AddressOf( treeVars, 'minimumErr' ), 'MinimumErr/F' )
  
  return tree, treeVars
  
# accessTTree()

def BookHistograms( hNames, nRows, nChimneysARow, nConnections, nChannels ):

  h = {}
  nXBins = nRows * nChimneysARow
  nYBins = nConnections * nChannels
  for hName in hNames.keys():
    h[hName] = ROOT.TH2F( hName, hName, nXBins, 0, nXBins, nYBins, 0, nYBins )

  return h
# BookHistograms()

if __name__ == "__main__":
  
  import argparse
  
  parser = argparse.ArgumentParser( description='Create a ROOT file containing a TTree with the statistics information.' )
  parser.add_argument( '-i', '--inputdir', dest = 'inFileDir', type = str, help = 'the directory of input files.' )
  parser.add_argument( '-o', '--outputfile', dest = 'outFile', type = str, help = 'the output file name.' )
  
  args = parser.parse_args()

  f = createOutROOTFile( args.outFile )
  t, tVars = accessTTree()
    
  rows = [ 'EE', 'EW', 'WE', 'WW' ]
  nChimneysARow = 20
  nConnections  = 18
  nPositions    = 8
  nChannels     = nPositions*4

  hNames = { 'AbsPeak': 'absPeak', 'Baseline': 'baseline', 'RMS': 'rms' }
  hList  = BookHistograms( hNames, len(rows), nChimneysARow, nConnections, nChannels )

  for row in rows:
    for iChimney in xrange( 1, nChimneysARow+1 ):
      for iConnection in xrange( 1, nConnections+1 ):
        for iPosition in xrange ( 1, nPositions+1 ):
          
          filelist = glob.glob('%s/CHIMNEY_%s%d/waveform_CH1_CHIMNEY_%s%02d_CONN_?%02d_POS_%d_*.csv' % ( args.inFileDir, row, iChimney, row, iChimney, iConnection, iPosition ))
          infile = 'blah'
          for ifile in filelist:
            if ifile:
              infile = ifile
              break
        
          # print infile
          if infile == 'blah': continue
          stats = drawWaveforms.statAllPositionAroundFile( infile )
  
          for ch in stats.keys():
            tVars.chimney = '%s%02d' % ( row, iChimney )
            tVars.connection = iConnection
            tVars.channel = ch
            tVars.nWaveforms = stats[ch]['nWaveforms']
            tVars.peak = stats[ch]['peak']['average']
            tVars.peakErr = stats[ch]['peak']['RMS']
            tVars.dip = stats[ch]['dip']['average']
            tVars.dipErr = stats[ch]['dip']['RMS']
            tVars.absPeak = stats[ch]['absPeak']['average']
            tVars.absPeakErr = stats[ch]['absPeak']['RMS']
            tVars.baseline = stats[ch]['baseline']['average']
            tVars.rms = stats[ch]['baseline']['RMS']
            tVars.maximum = stats[ch]['maximum']['average']
            tVars.maximumErr = stats[ch]['maximum']['error']
            tVars.minimum = stats[ch]['minimum']['average']
            tVars.minimumErr = stats[ch]['minimum']['error']
  
            print 'chimney %s, connection %d, channel %d, peak %f' % ( tVars.chimney, tVars.connection, tVars.channel, tVars.peak )
            t.Fill()
            
            for hName in hList.keys():
              iXBin = rows.index( row )*nChimneysARow + iChimney
              iYBin = ( iConnection - 1 )*nChannels + ch
              value = eval('tVars.%s' % hNames[hName])
              print iXBin, iYBin, value
              hList[hName].SetBinContent( iXBin, iYBin, value )
              if iXBin == 3:
                YBinLabel = 'Cable %02d, Ch %02d' % ( iConnection, ch )
                hList[hName].GetYaxis().SetBinLabel( iYBin, YBinLabel )
              if iYBin == 1:
                XBinLabel = '%s%02d' % ( row, iChimney )
                hList[hName].GetXaxis().SetBinLabel( iXBin, XBinLabel )
    
    for hName in hList.keys():
      hList[hName].Write()
    
  t.Write()
  f.Write()
