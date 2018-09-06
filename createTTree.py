#!/usr/bin/env python

import sys
import os
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
  Float_t baseline;\
  Float_t rms;\
  Float_t maximum;\
  Float_t maximumErr;\
  Float_t minimum;\
  Float_t minimumErr;\
};" );
# gROOT.ProcessLine


def createOutROOTFile( outFile ):
  f = ROOT.TFile( outFile, "UPDATE" )

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
  tree.Branch( 'Baseline', ROOT.AddressOf( treeVars, 'baseline' ), 'Baseline/F' )
  tree.Branch( 'RMS', ROOT.AddressOf( treeVars, 'rms' ), 'RMS/F' )
  tree.Branch( 'Maximum', ROOT.AddressOf( treeVars, 'maximum' ), 'Maximum/F' )
  tree.Branch( 'MaximumErr', ROOT.AddressOf( treeVars, 'maximumErr' ), 'MaximumErr/F' )
  tree.Branch( 'Minimum', ROOT.AddressOf( treeVars, 'minimum' ), 'Minimum/F' )
  tree.Branch( 'MinimumErr', ROOT.AddressOf( treeVars, 'minimumErr' ), 'MinimumErr/F' )
  
  return tree, treeVars
  
# accessTTree()

if __name__ == "__main__":
  
  import argparse
  
  parser = argparse.ArgumentParser( description='Create a ROOT file containing a TTree with the statistics information.' )
  parser.add_argument( '-i', '--inputdir', dest = 'inFileDir', type = str, help = 'the directory of input files.' )
  parser.add_argument( '-o', '--outputfile', dest = 'outFile', type = str, help = 'the output file name.' )
  
  args = parser.parse_args()

  f = createOutROOTFile( args.outFile )
  t, tVars = accessTTree()
  
  # for test
  infile = '%s/CHIMNEY_EW8/waveform_CH2_CHIMNEY_EW08_CONN_V18_POS_8_80.csv' % args.inFileDir
  stats = drawWaveforms.statAllPositionAroundFile( infile )
  
  for ch in stats.keys():
    tVars.chimney = 'EW08'
    tVars.connection = 18
    tVars.channel = ch
    tVars.nWaveforms = stats[ch]['nWaveforms']
    tVars.peak = stats[ch]['peak']['average']
    tVars.peakErr = stats[ch]['peak']['RMS']
    tVars.dip = stats[ch]['dip']['average']
    tVars.dipErr = stats[ch]['dip']['RMS']
    tVars.baseline = stats[ch]['baseline']['average']
    tVars.rms = stats[ch]['baseline']['RMS']
    tVars.maximum = stats[ch]['maximum']['average']
    tVars.maximumErr = stats[ch]['maximum']['error']
    tVars.minimum = stats[ch]['minimum']['average']
    tVars.minimumErr = stats[ch]['minimum']['error']
  
    print 'chimney %s, connection %d, peak %f' % ( tVars.chimney, tVars.connection, tVars.peak )
    t.Fill()
    
  t.Write()
  f.Write()
