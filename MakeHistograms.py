import argparse
import ROOT
import AccessROOTUtils

def BookHistograms( hNames, nRows, nChimneysARow, nConnections, nChannels ):

  h = {}
  nXBins = nRows * nChimneysARow
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

  f = AccessROOTUtils.createOutROOTFile( args.outFile )
  t = AccessROOTUtils.getTree( args.inFiles, 'ConnectivityAna' )
  

  rows = [ 'EE', 'EW', 'WE', 'WW' ]
  nChimneysARow = 20
  nConnections  = 18
  nPositions    = 8
  nChannels     = nPositions*4

  hNames = { 'AbsPeak': 'AbsPeak', 'Baseline': 'Baseline', 'RMS': 'RMS', 'PosPeak': 'Peak', 'NegPeak': 'Dip', 'Maximum': 'Maximum', 'Minimum': 'Minimum', 'AbsPeakRMS': 'AbsPeakErr', 'PosPeakRMS': 'PeakErr', 'NegPeakRMS': 'DipErr' }
  hList  = BookHistograms( hNames, len(rows), nChimneysARow, nConnections, nChannels )

  isXLabeled = [ False ]* ( len(rows)*nChimneysARow )
  isYLabeled = [ False ]* ( nConnections*nChannels )

  for i in t:
    # print 'Chimney: %s' % i.Chimney
    row = i.Chimney[0:2]
    iChimney = int( i.Chimney[2:4] )
    iXBin = rows.index( row )*nChimneysARow + iChimney
    iYBin = ( i.Connection - 1 )*nChannels + i.Channel
    XBinLabel = '%s%02d' % ( row, iChimney )
    YBinLabel = 'Cable %02d' % ( i.Connection )

    for hName in hList.keys():
      value = eval( 'i.%s' % hNames[hName] )
      hList[hName].SetBinContent( iXBin, iYBin, value )
      hList[hName].GetXaxis().SetBinLabel( iXBin, XBinLabel )
      if i.Channel == 1:
        hList[hName].GetYaxis().SetBinLabel( iYBin, YBinLabel )
        

  for hName in hList.keys():
    hList[hName].Write()

  f.Write()
