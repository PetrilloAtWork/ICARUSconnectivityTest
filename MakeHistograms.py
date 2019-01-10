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


def MakePlots( plotDir, pList, h ):

  for hName in pList:
    c = ROOT.TCanvas( hName, hName, 1600, 1200 )
    ROOT.gStyle.SetOptStat(0)
    c.SetRightMargin( 0.12 )

    if hName in [ 'PosPeak' ]:
      h[hName].GetZaxis().SetRangeUser( 0, 0.5 )
      h[hName].SetTitle("Positive Pulse Height")
    elif hName in [ 'Baseline' ]:
      h[hName].GetZaxis().SetRangeUser( -0.04, 0.02 )
    elif hName in [ 'RMS' ]:
      h[hName].GetZaxis().SetRangeUser( 0, 0.05 )
    elif hName in [ 'PosPeakToBaseline' ]:
      h[hName].GetZaxis().SetRangeUser( 0, 0.5 )
      h[hName].SetTitle("Positive Pulse Height / Baseline")
    
    h[hName].Draw("COLZ")
    pName = '%s/%s.pdf' % ( plotDir, hName )
    c.SaveAs( pName )

  return

# MakePlots


if __name__ == "__main__":
  
  parser = argparse.ArgumentParser( description='Create a ROOT file containing histograms with the statistics information.' )
  parser.add_argument( 'inFiles', metavar = 'i', type = str, nargs = '+', help = 'the input files.' )
  parser.add_argument( '-o', '--outputfile', dest = 'outFile', type = str, help = 'the output file name.' )
  parser.add_argument( '-p', '--plotdir', dest = 'plotDir', type = str, help = 'the directory of output plots.' )

  args = parser.parse_args()

  f = AccessROOTUtils.createOutROOTFile( args.outFile )
  t = AccessROOTUtils.getTree( args.inFiles, 'ConnectivityAna' )
  

  rows = [ 'EE', 'EW', 'WE', 'WW' ]
  nChimneysARow = 20
  nConnections  = 18
  nPositions    = 8
  nChannels     = nPositions*4

  hNames = { 'AbsPeak': 'AbsPeak', 'Baseline': 'Baseline', 'RMS': 'RMS', 'PosPeak': 'Peak', 'NegPeak': 'Dip', 'Maximum': 'Maximum', 'Minimum': 'Minimum', 'AbsPeakRMS': 'AbsPeakErr', 'PosPeakRMS': 'PeakErr', 'NegPeakRMS': 'DipErr', 'PosPeakToBaseline': 'PosPeakToBaseline', 'NegPeakToBaseline': 'NegPeakToBaseline', 'AbsPeakToBaseline': 'AbsPeakToBaseline' }
  pList = [ 'PosPeak', 'Baseline', 'RMS' ]
  # pList = [ 'PosPeak', 'Baseline', 'RMS', 'PosPeakToBaseline' ]
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
      value = 0.
      if hName in [ 'PosPeakToBaseline', 'NegPeakToBaseline', 'AbsPeakToBaseline' ]:
        variable = hName[0:7]
        numerator = eval( 'i.%s' % hNames[variable] )
        denominator = i.Baseline
        if denominator < 1.e-9:
          value = 0.
        else:
          value = numerator/denominator
      else:
        value = eval( 'i.%s' % hNames[hName] )
        
      hList[hName].SetBinContent( iXBin, iYBin, value )
      hList[hName].GetXaxis().SetBinLabel( iXBin, XBinLabel )
      if i.Channel == 1:
        hList[hName].GetYaxis().SetBinLabel( iYBin, YBinLabel )
        

  for hName in hList.keys():
    hList[hName].Write()

  f.Write()

  if args.plotDir:
    MakePlots( args.plotDir, pList, hList )
