import argparse
import ROOT
import AccessROOTUtils

def BookHistograms( hNames, nConditions, nConnections, nChannels ):

  h = {}
  nXBins = nConditions
  nYBins = nConnections * nChannels
  for hName in hNames.keys():
    h[hName] = ROOT.TH2F( hName, hName, nXBins, 0, nXBins, nYBins, 0, nYBins )

  return h
# BookHistograms()

if __name__ == "__main__":
  
  parser = argparse.ArgumentParser( description='Create a ROOT file containing histograms with the statistics information.' )
  parser.add_argument( 'inFiles', metavar = 'i', type = str, nargs = '+', help = 'the input files.' )
  parser.add_argument( '-o', '--outputfile', dest = 'outFile', type = str, help = 'the output file name.' )
  # parser.add_argument( '-p', '--plotdir', dest = 'plotDir', type = str, help = 'the directory of output plots.' )

  args = parser.parse_args()

  if len( args.inFiles ) > 2:
    raise RunTimeError('Cannot deal with more than 2 input files!')

  f = AccessROOTUtils.createOutROOTFile( args.outFile )
  file1 = [ args.inFiles[0] ]
  print 'Processing input file 1: %s' % file1
  t1 = AccessROOTUtils.getTree( file1, 'ConnectivityAna' )
  file2 = [ args.inFiles[1] ]
  print 'Processing input file 2: %s' % file2
  t2 = AccessROOTUtils.getTree( file2, 'ConnectivityAna' )
  

  Conditions = [ 'Normal', 'S14 Disconnected' ]
  nConnections  = 18
  nPositions    = 1
  iPosition     = 2
  nChannels     = nPositions*4

  hNames = { 'AbsPeak': 'AbsPeak', 'Baseline': 'Baseline', 'RMS': 'RMS', 'PosPeak': 'Peak', 'NegPeak': 'Dip', 'Maximum': 'Maximum', 'Minimum': 'Minimum', 'AbsPeakRMS': 'AbsPeakErr', 'PosPeakRMS': 'PeakErr', 'NegPeakRMS': 'DipErr' }
  hList  = BookHistograms( hNames, len(Conditions), nConnections, nChannels )


  for i in t1:
    # print 'Chimney: %s' % i.Chimney
    row = i.Chimney[0:2]
    iChimney = int( i.Chimney[2:4] )
    iXBin = 1
    iYBin = ( i.Connection - 1 )*nChannels + i.Channel - ( iPosition - 1 )*4
    XBinLabel = '%s' % ( Conditions[0] )
    YBinLabel = 'Cable %02d' % ( i.Connection )

    for hName in hList.keys():
      value = eval( 'i.%s' % hNames[hName] )
      hList[hName].SetBinContent( iXBin, iYBin, value )
      hList[hName].GetXaxis().SetBinLabel( iXBin, XBinLabel )
      if i.Channel == 5:
        hList[hName].GetYaxis().SetBinLabel( iYBin, YBinLabel )

  for i in t2:
    # print 'Chimney: %s' % i.Chimney
    row = i.Chimney[0:2]
    iChimney = int( i.Chimney[2:4] )
    iXBin = 2
    iYBin = ( i.Connection - 1 )*nChannels + i.Channel - ( iPosition - 1 )*4
    XBinLabel = '%s' % ( Conditions[1] )
    YBinLabel = 'Cable %02d' % ( i.Connection )

    for hName in hList.keys():
      value = eval( 'i.%s' % hNames[hName] )
      hList[hName].SetBinContent( iXBin, iYBin, value )
      hList[hName].GetXaxis().SetBinLabel( iXBin, XBinLabel )
      if i.Channel == 5:
        hList[hName].GetYaxis().SetBinLabel( iYBin, YBinLabel )


  for hName in hList.keys():
    hList[hName].Write()

  f.Write()
