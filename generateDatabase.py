#!/usr/bin/env python

__doc__ = """
Converts the connectivity analysis results from the specified file into a
comma-separated value file.
"""
__version__ = "1.0"

import sys
import os
import logging
import csv
import time
import drawWaveforms

logging.basicConfig(level=logging.INFO)


### --- BEGIN python utilities -------------------------------------------------
def makeList(obj):
  return obj if isinstance(obj, (list, tuple)) else ( obj, )


def paddingFor(n): return len(str(n))


def composeFunctions(f = None, g = None):
  if f is None:
    return (lambda x: x) if g is None else g
  else:
    return f if g is None else lambda *args, **kargs: g(f(*args, **kargs))
# composeFunctions()


### --- END python utilities ---------------------------------------------------

### --- BEGIN ROOT utilities ---------------------------------------------------
def parseROOTpath(path):
  """Returns a 3-ple (file path, ROOT path, object name)."""
  
  Suffix = ".root"
  ROOTpathSep = '/'
  
  #
  # 1. determine the file name (ending with `.root` or with a ':'
  # 
  
  for sep in (Suffix + ':', Suffix + ROOTpathSep, Suffix, ':', ):
    iSep = path.find(sep)
    if iSep != -1: break
  else: return ( path, "", "")
  
  if path[iSep:].startswith(Suffix):
    iSep += len(Suffix)
  fileName = path[:iSep]
  try:
    while path[iSep] in ( ':', ROOTpathSep, ): iSep += 1
  except IndexError: pass # if we got to the end of the string, it's ok
  
  #
  # 2. deal with the ROOT path (last element is the object name; may be empty)
  #
  ROOTpath = path[iSep:].split(ROOTpathSep)
  if len(ROOTpath) == 0:
    objPath = ""
    objName = ""
  else:
    objPath = filter(bool, ROOTpathSep).join(ROOTpath[:-1]) # omit empty names
    objName = ROOTpath[-1]
  #
  
  return fileName, objPath, objName
# parseROOTpath()

# ------------------------------------------------------------------------------
def fetchROOTobject(filePath, ROOTpath, ROOTname, objClasses = None):
  """Returns a pair (ROOT directory, ROOT object).
  
  The argument `filePath` may be the path to the ROOT file, or it can be an
  already opened `TFile` or `TDirectory`, in which case that object will be used
  as a starting point for `ROOTpath`.
  
  If `objClass` is specified, the object will be checked to derive from
  `objClass` via `TClass::InheritsFrom()`, which accepts either a `TClass`
  object or a class name.
  """
  
  #
  # 1. open the ROOT file
  #
  if isinstance(filePath, ROOT.TDirectory):
    ROOTfile = filePath
  else:
    ROOTfile = ROOT.TFile(filePath, "READ")
    if not ROOTfile:
      raise RuntimeError("Unable to open ROOT file '{}'.".format(filePath))
  # else`
    
  assert(ROOTfile)
  
  #
  # 2. fetch the ROOT directory
  #
  if ROOTpath:
    ROOTdir = ROOTdir.GetDirectory(ROOTpath)
    if not ROOTdir:
      raise RuntimeError(
        "Unable to open ROOT directory '{}:{}'."
        .format(ROOTfile.GetPath(), ROOTpath)
        )
    # if no directory
  else:
    ROOTdir = ROOTfile
  
  #
  # 3. fetch the ROOT object
  #
  
  if ROOTname:
    ROOTobj = ROOTdir.Get(ROOTname)
    if not ROOTobj:
      raise RuntimeError(
        "Can't find object '{}' in ROOT directory '{}'."
        .format(ROOTname, ROOTdir.GetPath())
        )
    # if object not found
  else:
    ROOTobj = ROOTdir
  
  #
  # 4. type check, if requested
  #
  if objClasses:
    objClassNames = []
    for objClass in makeList(objClasses):
      if not isinstance(objClass, ( basestring, ROOT.TClass, )):
        objClass = objClass.Class() # assume it's an instance of ROOT object
      if ROOTobj.InheritsFrom(objClass): break
      objClassNames.append \
       (objClass.GetName() if isinstance(objClass, ROOT.TClass) else objClass)
    else:
      raise RuntimeError(
        "Object '{}' in ROOT directory '{}' is of unexpected type '{}' incompatible with '{}'."
        .format(
          ROOTobj.GetName(), ROOTdir.GetPath(),
          ROOTobj.IsA().GetName(),
          "', '".join(objClassNames)
          )
        )
    # for ... else (type check failed)
    
  # if type check requested
  
  return ROOTdir, ROOTobj
  
# fetchROOTobject()


### --- END ROOT utilities -----------------------------------------------------

### --- BEGIN data extraction and processing -----------------------------------
class InfoExtractor(object):
  
  class Field(object):
    def __init__(self, key, action = None, name = None, postprocess = None):
      self.key = key
      self.name = name if name else self.key
      self.action = self.extractEntry if action is None else action
      self.post = postprocess if postprocess else (lambda x: x)
    # __init__()
    
    def extract(self, data, *args, **kargs):
      return self.post(self._runAction(data, *args, **kargs))
    
    def makeEntry(self, data, *args, **kargs):
      return (self.name, self.extract(data, *args, **kargs)) if self.name \
        else None
    # def makeEntry()
    
    @staticmethod
    def extractEntry(data, fieldName):
      value = getattr(data, fieldName)
      if isinstance(value, str):
         while value.endswith('\0'): value = value[:-1]
      return value
    # extractEntry()
    
    def _runAction(self, data, *args, **kargs):
      return self.action(data, self.key, *args, **kargs)
    
  # class Field
  
  class WaveformSourceInfoMaker(Field):
    def __init__(self, name = "", postprocess = None, testName = "PULSE"):
      InfoExtractor.Field.__init__(self, "",
        action=self.makeWaveformSourceInfo,
        name=name, postprocess=postprocess,
        )
      self.testName = testName
    # __init__()
    
    def makeWaveformSourceInfo(self, data, _):
      return drawWaveforms.WaveformSourceInfo(
        chimney=InfoExtractor.Field.extractEntry(data, 'Chimney'),
        connection=InfoExtractor.Field.extractEntry(data, 'Connection'),
        channel=InfoExtractor.Field.extractEntry(data, 'Channel'),
        index=None,
        testName=self.testName,
        )
    # makeWaveformSourceInfo()
  # class WaveformSourceInfoMaker
    
  class WaveformSourceFilePath(WaveformSourceInfoMaker):
    def __init__(self,
     name = "", postprocess = None, testName = "PULSE", waveformDir = ""
     ):
      InfoExtractor.WaveformSourceInfoMaker.__init__(self,
        name=name,
        postprocess=composeFunctions(self.makeWaveformSourceFilePath, postprocess),
        )
      self.testName = testName
      self.waveformDir = waveformDir
    # __init__()
    
    def makeWaveformSourceFilePath(self, sourceInfo):
      if not self.waveformDir: return None
      waveformDir = os.path.join(self.waveformDir, 
       sourceInfo.formatString
        (drawWaveforms.WaveformSourceFilePath.StandardDirectory)
       )
      return drawWaveforms.WaveformSourceFilePath \
        (sourceInfo, sourceDir=waveformDir)
    # makeWaveformSourceFilePath()
    
  # class WaveformSourceFilePath
    
  class ExtractCryostat(WaveformSourceInfoMaker):
    def __init__(self, name, postprocess = None):
      InfoExtractor.WaveformSourceInfoMaker.__init__(self,
        name=name,
        postprocess=composeFunctions(InfoExtractor.ExtractCryostat.extractCryostat, postprocess),
        )
    # __init__()
    
    @staticmethod
    def extractCryostat(sourceInfo): return sourceInfo.cryostat()
    
  # class ExtractCryostat
    
  class ExtractTPC(WaveformSourceInfoMaker):
    def __init__(self, name, postprocess = None):
      InfoExtractor.WaveformSourceInfoMaker.__init__(self,
        name=name,
        postprocess=composeFunctions(InfoExtractor.ExtractTPC.extractTPC, postprocess),
        )
    # __init__()
    @staticmethod
    def extractTPC(sourceInfo): return sourceInfo.TPC()
    
  # class ExtractTPC
  
  class ExtractChannelTestTimestamp(WaveformSourceFilePath):
    """Test time is taken from the waveform file timestamps (average),
    or from the metadata file content, whichever is earlier.
    No time zone conversions are explicitly performed, and the resulting time is 
    supposedly in the local time of the DAQ node.
    The value is in seconds from the epoch; the Wise Man says:
    epoch = time.gmtime(0.0)
    """
    def __init__(self, name, waveformDir = None, postprocess = None):
      InfoExtractor.WaveformSourceFilePath.__init__(self,
        name=name,
        postprocess=composeFunctions(InfoExtractor.ExtractChannelTestTimestamp.waveformTimestamp, postprocess),
        waveformDir=waveformDir,
        )
    # __init__()
    
    @staticmethod
    def metadataFilePath(sourcePath):
      # first look for the metadata file
      dir_ = os.path.join(sourcePath.buildDir())
      return os.path.join(dir_, "INFO-%s.txt" % os.path.basename(dir_))
    # metadataFilePath()
    
    
    @staticmethod
    def metadataTestTime(metadataPath):
      # look for the first line starting with "Date:"
      with open(metadataPath, 'r') as metadataFile:
        DateTag = 'Date'
        for line in metadataFile:
          if not line.startswith(DateTag + ":"): continue
          timeString = line[len(DateTag) + 1:].strip()
          try: return time.mktime(time.strptime(timeString))
          except Exception, e:
            logging.debug("Metadata time parsing ('%s') failed: %s.",
              timeString, str(e))
          # try ... except
        # for
      # with
      logging.debug \
       ("Could not extract time from metadata file '%s'", metadataFile)
      return None
    # metadataTestTime()
    
    @staticmethod
    def metadataFileTime(metadataPath):
      try: return os.stat(metadataPath).st_mtime
      except OSError: return None
    # metadataFileTime()
    
    @staticmethod
    def averageWaveformFileTimestamp(sourcePath):
      # if missing, rely on the timestamp of the waveform files
      waveformFiles = sourcePath.allChannelSources()
      fileTimes = []
      for waveformFile in waveformFiles:
        try: fileStat = os.stat(waveformFile)
        except OSError: continue # not found
        fileTimes.append(fileStat.st_mtime) # last modification time
      # for
      return sum(fileTimes) / len(fileTimes) if fileTimes else None
    # averageWaveformFileTimestamp()
    
    @staticmethod
    def waveformTimestamp(sourcePath):
      # first look for the metadata file
      metadataFile \
       = InfoExtractor.ExtractChannelTestTimestamp.metadataFilePath(sourcePath)
      metaTime = None
      if os.path.exists(metadataFile):
        metaTime \
         = InfoExtractor.ExtractChannelTestTimestamp.metadataTestTime(metadataFile)
        if metaTime is None:
          metaTime \
           = InfoExtractor.ExtractChannelTestTimestamp.metadataFileTime(metadataFile)
        # if      # if has metadata file
      
      # if missing, rely on the timestamp of the waveform files
      aveTime \
       = InfoExtractor.ExtractChannelTestTimestamp.averageWaveformFileTimestamp(sourcePath)
      if aveTime is not None:
        return aveTime if metaTime is None else min(aveTime, metaTime)
      return metaTime if metaTime is not None else ""
    # waveformTimestamp()
    
  # class ExtractChannelTestTimestamp
  
  def __init__(self, *fields):
    self.fields = list(fields) # copy
  
  def __call__(self, data): return self.extract(data)
  
  def addField(self, *args, **kargs):
    assert len(args) >= 1
    
    try: isFieldClass = issubclass(args[0], InfoExtractor.Field)
    except TypeError: isFieldClass = False
    
    if isinstance(args[0], InfoExtractor.Field):
      assert len(args) == 1
      field = args[0]
    elif isFieldClass:
      field = args[0](*args[1:], **kargs)
    else:
      field = InfoExtractor.Field(*args, **kargs)
    self.fields.append(field)
    return self
  # addField()
  
  def extract(self, data):
    return dict(filter(bool, (field.makeEntry(data) for field in self.fields)))
  
  def toc(self):
    return [ field.name for field in self.fields ]
  
# class InfoExtractor

### --- END data extraction and processing -------------------------------------

### --- BEGIN main program -----------------------------------------------------
if __name__ == "__main__":
  import argparse
  
  Parser = argparse.ArgumentParser(description=__doc__)
  
  class OutputFileModes:
    NewFile   = "newfile"
    Truncate  = "overwrite"
    Append    = "append"
    
    @staticmethod
    def modes():
      return [
        OutputFileModes.NewFile,
        OutputFileModes.Truncate,
        OutputFileModes.Append,
        ]
    # modes()
    
  # class OutputFileModes
  
  Parser.set_defaults(
    treepath="",
    treename="ConnectivityAna",
    outputFormat="excel",
    outputFileMode=OutputFileModes.NewFile,
    )
  
  
  Parser.add_argument("InputFile", nargs="?",
    help="ROOT file with the analysis tree (may contain ROOT path to tree too)")
  
  Parser.add_argument("--debug", "-d", action="count",
    help="enables debugging messages")
  
  argGroup = Parser.add_argument_group(title="Input options")
  argGroup.add_argument("--treepath", "-p", default="",
    help="ROOT path of the tree within the input file (tree name excluded)")
  argGroup.add_argument("--treename", "-t",
    help="name of the tree within the input file ['%(default)s']")
  argGroup.add_argument("--waveformdir",
    help="directory where to find the waveform files")
  
  argGroup = Parser.add_argument_group(title="Output options")
  argGroup.add_argument("--outputfile", "-o",
    help="name of the output file (on screen by default)")
  argGroup.add_argument("--format", "-f", dest="outputFormat",
    help="use the specified CSV format ['%(default)s']")
  argGroup.add_argument("--noheader", "-H", action="store_true",
    help="omit the header from output file ['%(default)s']")
  argGroup.add_argument("--listformats", "-L", dest="listOutputFormats",
    action="store_true", help="prints all the supported formats")
  argGroup.add_argument("--mode", "-O", dest="outputFileMode",
    choices=OutputFileModes.modes(),
    help="output file mode [%(default)s]")
  
  """
  argGroup = Parser.add_argument_group(title="Numerical output format")
  argGroup.add_argument("--integer", "-d", "-i", action="store_false",
    dest="bFloat", help="sets the sum of integral numbers")
  argGroup.add_argument("--real", "--float", "-e", "-f", "-g", 
    action="store_true", dest="bFloat", help="sets the sum of real numbers")
  argGroup.add_argument("--enable-commands", "-C", action="store_true",
    dest="bCommands", help="enables special commands (see help)")
  argGroup.add_argument("--radix", type=int, dest="Radix", default=0,
    help="radix of integer numbers (0: autodetect) [%(default)d]")
  
  argGroup = Parser.add_argument_group(title="Output arrangement")
  
  columnOptions = argGroup.add_mutually_exclusive_group()
  columnOptions.add_argument("--columns", "-c", 
    action="append", dest="Columns", default=[],
    help="sets column mode and the columns to be included, comma separated"
      " (first is 1)")
  columnOptions.add_argument("--allcolumns",
    action="store_true", dest="AllColumns", default=False,
    help="sets column mode and uses all available columns")
  
  argGroup.add_argument("--colnumber", "-l", 
    action="store_true", dest="ColNumber",
    help="writes the column number in the output [default: only when needed]")
  argGroup.add_argument("--nocolnumber", "-L",
    action="store_false", dest="ColNumber",
    help="omits the column number in the output [default: only when needed]")
  
  argGroup = Parser.add_argument_group(title="Statistics output")
  argGroup.add_argument("--average", "-a",
    dest="Print", action="append_const", const="average",
    help="prints the average of the input")
  argGroup.add_argument("--sum", "-s",
    dest="Print", action="append_const", const="sum",
    help="prints the sum of the input")
    """
  
  Parser.add_argument('--version', action="version",
    version="%(prog)s version {}".format(__version__)
    )
  
  args = Parser.parse_args()
  
  logging.getLogger().setLevel \
    (logging.DEBUG - (args.debug - 1) if args.debug else logging.INFO)
  
  if args.listOutputFormats:
    logging.info("Supported CSV formats: '{}'.".format(
      "', '".join(csv.list_dialects())
      ))
    sys.exit(0)
  # if list output formats
  
  if not args.InputFile:
    raise RuntimeError("An input ROOT file must be specified.")
  
  
  # we import ROOT after parsing the options so that it does not mess with the
  # command line arguments
  import ROOT

  #
  # parse input options and open the input tree
  # 
  # The path specified as argument is tried first.
  # If it is a ROOT tree, we are good (but no ROOT directory must have been
  # specified as option).
  # If the path is a ROOT directory (or just a ROOT file), the option values
  # are used to fetch a ROOT tree within that ROOT directory (default ROOT
  # subpath is none, while the tree does have a default name).
  # In the end, the final object has better to be a `TTree`.
  #
  
  # we are actually not sure whether `ROOTtreeName` is the name of the tree
  # or not
  ROOTfilePath, ROOTtreePath, ROOTtreeName = parseROOTpath(args.InputFile)
  
  SrcDir, SrcTree \
    = fetchROOTobject(ROOTfilePath, ROOTtreePath, ROOTtreeName)
  if isinstance(SrcTree, ROOT.TDirectory):
    SrcDir = SrcTree
    SrcDir, SrcTree \
      = fetchROOTobject(SrcDir, args.treepath, args.treename, ROOT.TTree)
  elif not isinstance(SrcTree, ROOT.TTree):
    raise RuntimeError(
     "ROOT object '{}:{}' is a '{}', not a TTree."
     .format(SrcDir.GetPath(), SrcTree.GetName(), SrcTree.IsA().GetName())
     )
  elif args.treepath:
    raise RuntimeError(
     "ROOT tree path specified both via input file (as '{}') and via option (as '{}')"
     .format(ROOTtreePath, args.treepath)
     )
  # if 
  
  nEntries = SrcTree.GetEntries()
  logging.info("Tree '{}:{}' has {} entries.".format(
    SrcDir.GetPath(), SrcTree.GetName(), nEntries,
    ))
  
  logging.debug("Available information:\n{}".format(
    "\n".join([ leaf.GetName() for leaf in SrcTree.GetListOfLeaves() ])
    ))
  
  #
  # prepare output file
  #
  if args.outputfile:
    if   args.outputFileMode == OutputFileModes.Truncate: mode = 'w'
    elif args.outputFileMode == OutputFileModes.Append:   mode = 'a'
    elif args.outputFileMode == OutputFileModes.NewFile:
      if os.path.exists(args.outputfile):
        raise RuntimeError \
          ("Output file '{}' already exists.".format(args.outputfile))
      # if
      mode = 'w'
    # select mode
    logging.debug("Opening '{}', mode='{}'".format(args.outputfile, mode))
    OutputFile = open(args.outputfile, mode)
  else:
    OutputFile = sys.stdout
  
  #
  # prepare the information to be extracted
  #
  extractData = InfoExtractor(
    InfoExtractor.ExtractCryostat('Cryostat'),
    InfoExtractor.ExtractTPC('TPC'),
    InfoExtractor.Field('ChimneyRow', name="ChimneyNo"),
    InfoExtractor.Field('Connection'),
    InfoExtractor.Field('Channel'),
    InfoExtractor.Field('AbsPeak'),
    InfoExtractor.Field('AbsPeakErr'),
    InfoExtractor.Field('Peak', name='peak'),
    InfoExtractor.Field('Dip'),
    InfoExtractor.Field('RMS'),
    InfoExtractor.ExtractChannelTestTimestamp('testTime', waveformDir=args.waveformdir),
    )
  
  CSVwriter = csv.DictWriter \
    (OutputFile, dialect=args.outputFormat, fieldnames=extractData.toc())
  
  if not args.noheader: CSVwriter.writeheader()
  
  
  for iEntry, channelResults in enumerate(SrcTree):
    channelFields = extractData(channelResults)
    if iEntry % 5000 == 0:
      logging.debug("[#%*d] %s", paddingFor(nEntries-1), iEntry, channelFields)
    CSVwriter.writerow(channelFields)
  # for
  
  # we let ROOT close its stuff
  
  nErrors = 0
  
  if nErrors > 0:
    logging.error("%d errors found.", nErrors)
    sys.exit(1)
  sys.exit(0)
### --- END main program -------------------------------------------------------

