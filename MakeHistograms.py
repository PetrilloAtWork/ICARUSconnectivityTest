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

def BookHistogramsForHorizontalWires( hNames, nRows, nChimneyARow, nConnections, nChannels ):
  
  h = {}
  nXBins = nRows * 2 * nChimneyARow
  nYBins = nConnections * nChannels
  for hName in hNames.keys():
    hName = 'Horizontal%s' % hName
    h[hName] = ROOT.TH2F( hName, hName, nXBins, 0, nXBins, nYBins, 0, nYBins )
  
  return h
# BookHistogramsForHorizontalWires()

def MakePlots( plotDir, pList, h, doHorizontal = False ):

  for hName in pList:
    if doHorizontal:
      hName = 'Horizontal%s' % hName
    c = ROOT.TCanvas( hName, hName, 1600, 1200 )
    ROOT.gStyle.SetOptStat(0)
    c.SetRightMargin( 0.12 )

    if hName in [ 'PosPeak' ]:
      h[hName].GetZaxis().SetRangeUser( 0, 0.5 )
      h[hName].SetTitle("Positive Pulse Height")
    elif hName in [ 'HorizontalPosPeak' ]:
      h[hName].GetZaxis().SetRangeUser( 0, 0.25 )
      h[hName].SetTitle("Positive Pulse Height of Horizontal Wires")
    elif hName in [ 'Baseline' ]:
      h[hName].GetZaxis().SetRangeUser( -0.05, 0.03 )
    elif hName in [ 'HorizontalBaseline' ]:
      h[hName].GetZaxis().SetRangeUser( -0.05, 0.2 )
      h[hName].SetTitle("Baseline of Horizontal Wires")
    elif hName in [ 'RMS' ]:
      h[hName].GetZaxis().SetRangeUser( 0, 0.05 )
    elif hName in [ 'HorizontalRMS' ]:
      h[hName].GetZaxis().SetRangeUser( 0, 0.15 )
      h[hName].SetTitle("RMS of Horizontal Wires")
      
    elif hName in [ 'PosPeakToBaseline', 'HorizontalPosPeakToBaseline' ]:
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
  parser.add_argument( '-t', '--horizontal', dest = 'doHorizontal', type = bool, help = 'whether we want to make plots for horizontal wires.' )

  args = parser.parse_args()

  f = AccessROOTUtils.createOutROOTFile( args.outFile )
  t = AccessROOTUtils.getTree( args.inFiles, 'ConnectivityAna' )
  

  rows = [ 'EE', 'EW', 'WE', 'WW' ]
  nChimneysARow = 20
  nConnections  = 18
  nPositions    = 8
  nChannels     = nPositions*4
  nChimneyARowHorizontal = 2
  nConnectionsHorizontal = 33

  hNames = { 'AbsPeak': 'AbsPeak', 'Baseline': 'Baseline', 'RMS': 'RMS', 'PosPeak': 'Peak', 'NegPeak': 'Dip', 'Maximum': 'Maximum', 'Minimum': 'Minimum', 'AbsPeakRMS': 'AbsPeakErr', 'PosPeakRMS': 'PeakErr', 'NegPeakRMS': 'DipErr', 'PosPeakToBaseline': 'PosPeakToBaseline', 'NegPeakToBaseline': 'NegPeakToBaseline', 'AbsPeakToBaseline': 'AbsPeakToBaseline' }
  pList = [ 'PosPeak', 'Baseline', 'RMS' ]
  # pList = [ 'PosPeak', 'Baseline', 'RMS', 'PosPeakToBaseline' ]
  hList  = BookHistograms( hNames, len(rows), nChimneysARow, nConnections, nChannels )
  htList = BookHistogramsForHorizontalWires( hNames, len(rows), nChimneyARowHorizontal, nConnections, nChannels )

  isXLabeled = [ False ]* ( len(rows)*nChimneysARow )
  isYLabeled = [ False ]* ( nConnections*nChannels )

  for i in t:
    # print 'Chimney: %s' % i.Chimney
    row = i.Chimney[0:2]
    iChimney = int( i.Chimney[2:4] )
    if args.doHorizontal and ( iChimney == 1 or iChimney == 20 ):
      iSubX = i.Connection/ ( nConnections + 1 )
      iXBin = rows.index( row )*2*nChimneyARowHorizontal + int( iChimney == 20 )*2 + iSubX + 1
      iYBin = ( i.Connection - iSubX * nConnections - 1 )*nChannels + i.Channel
      # print row, rows.index( row ), iChimney, i.Connection, i.Channel, iXBin, iYBin
      XBinLabel = '%s%02d-%d' %( row, iChimney, iSubX )
      YBinLabel = 'Cable %02d' % ( i.Connection )
    else:
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

      if args.doHorizontal and ( iChimney == 1 or iChimney == 20 ):
        htName = 'Horizontal%s' % hName
        htList[htName].SetBinContent( iXBin, iYBin, value )
        htList[htName].GetXaxis().SetBinLabel( iXBin, XBinLabel )
      else:
        hList[hName].SetBinContent( iXBin, iYBin, value )
        hList[hName].GetXaxis().SetBinLabel( iXBin, XBinLabel )
      if i.Channel == 1:
        if args.doHorizontal and ( iChimney == 1 or iChimney == 20 ) and ( i.Connection/ ( nConnections + 1 ) == 0 ):
          htList[htName].GetYaxis().SetBinLabel( iYBin, YBinLabel )
        elif ( iChimney > 1 ) and ( iChimney < 20 ):
          hList[hName].GetYaxis().SetBinLabel( iYBin, YBinLabel )


  for hName in hList.keys():
    hList[hName].Write()
  for hName in htList.keys():
    htList[hName].Write()

  f.Write()

  if args.plotDir:
    MakePlots( args.plotDir, pList, hList )
    if args.doHorizontal:
      MakePlots( args.plotDir, pList, htList, args.doHorizontal )
