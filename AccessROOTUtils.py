import sys
import ROOT


def createOutROOTFile( outFile ):
  # f = ROOT.TFile( outFile, "UPDATE" )
  f = ROOT.TFile( outFile, "RECREATE" )

  if not f:
    print >> sys.stderr, "Cannot open %s" % outFile
    sys.exit( 1 )

  return f

# createOutROOTFile()

def getTree( fNames, tName ):
  
  t = ROOT.TChain( tName )
  for fName in fNames:
    t.AddFile( fName )
  
  t.SetDirectory(0)
  return t

# getTree()
