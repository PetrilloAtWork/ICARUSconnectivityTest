import testDriver, stopwatch
import logging
import sys

__all__ = [ "fullCycleTest", ]

def fullCycleTest(
 config = "TestConfig.ini",
 chimney = "EW00",
 **kargs
 ):
  reader = None
  globalTimer = stopwatch.StopWatch()
  try:
    
    timer = stopwatch.StopWatch()
    
    logging.info("fullCycleTest(): ChimneyReader setup")
    kargs['configurationFile'] = config
    kargs['chimney'] = chimney
    timer.restart()
    reader = testDriver.ChimneyReader(**kargs)
    timer.stop()
    logging.info("fullCycleTest(): ChimneyReader setup ended in {}".format(timer.toString()))
    if not reader.scope: raise RuntimeError("Failed to contact the oscilloscope.")
    
    logging.info("fullCycleTest(): readout loop")
    timer.restart()
    reader.start()
    iRead = 0
    while reader.readNext():
      iRead += 1
      print("Read #{}".format(iRead))
    # while
    timer.stop()
    logging.info("fullCycleTest(): readout ended in {}".format(timer.toString()))
    
    logging.info("fullCycleTest(): verification")
    timer.restart()
    success = reader.verify()
    timer.stop()
    logging.info("fullCycleTest(): verification ended in {}".format(timer.toString()))
    if not success:
      raise RuntimeError("Verification failed!")
    
    logging.info("fullCycleTest(): archival script generation")
    timer.restart()
    reader.generateArchivalScript()
    timer.stop()
    logging.info("fullCycleTest(): script generation ended in {}".format(timer.toString()))
    
  except Exception as e:
    print >>sys.stderr, e
  globalTimer.stop()
  logging.info("fullCycleTest(): test took {}".format(globalTimer.toString()))
  if reader:
    reader.printTimers()
  return reader
# fullCycleTest()


if __name__ == "__main__":
  import sys
  fullCycleTest(fake=True)
  sys.exit(0)
# main
