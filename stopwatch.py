#!/usr/bin/env python

__doc__ = """Yet another stopwatch class.

I might really like to write this stuff.
This might be the third time just in Python.
"""
__all__ = [ "StopWatch", "WatchCollection", ]

from timeit import default_timer as time


class StopWatch:
  """A class keeping track of the time.
  
  This class is a single stopwatch which keeps track of elapsing time.
  It can be started, paused, resumed, stopped and reset, and total and running
  time can be requested at any time.
  
  The total time is the time elapsed while the stopwatch was running.
  Due to the functionality of pausing, that time is made of the sum of all the
  contiguous run periods that the watch has seen from the last reset, which are
  separated by pauses. A run can be completed or still running: only the last
  run can in fact being still running, and if there is a pause none is.
  The watch keeps track of the sum of all the completed runs, and also of the
  partial time of the running one (if the watch is paused, this time is 0).
  
  All times are in seconds.
  
  Example:
      
      from stopwatch import StopWatch
      watch = StopWatch() # started!
      
      # ... do something ...
      
      watch.pause()
      print "Time elapsed for the first task:", watch
      
  Another usage pattern is in conjunction with the `with` statement:
      
      watch = StopWatch(startNow=False)
      
      for iValue, value in enumerate(data):
        
        print("Start processing item #{:d}:\n  {}".format(iValue, value))
        
        with watch as w:
          res = elaborate(data)
          validate(res)
          print "...", w.partial(),
        
        print(" => result: {}".format(res))
        
      else: iValue += 1
      
      print("Processing of {:d} values took {}"
        .format(iValue, watch.toString("ms"))
        )
      
  will time the `elaborate()`/`validate()` portion of the loop, but not the
  preliminary introduction rendering the data being processed on screen and
  the final rendering of the results. Note that outside `with`, the partial
  time is not available any more, so the only way to observe it, if desired,
  is from inside the `with` statement.
  """
  def __init__(self, startNow = True):
    """Prepares the stopwatch, and starts it immediately.
    
    If `startNow` is set to `False`, the stopwatch is created stopped, otherwise
    it is created running.
    """
    self._stored = 0.0 # time to be added to the current running timer
    self._startTime = None # when last timer run started (None if not running)
    self._runs = 0 # number of runs seen so far (including the running one)
    if startNow: self.start()
  # __init__()
  
  @staticmethod
  def timer():
    """The timer used to read the current time."""
    return time()
  
  @staticmethod
  def timeSince(startTime):
    """Returns the time elapsed from `startTime` (0 if the latter is `None`)."""
    return 0.0 if startTime is None else StopWatch.timer() - startTime
  
  def paused(self): return self._startTime is None
  def stopped(self): return self.paused()
  def running(self): return not self.paused()
  def runs(self): return self._runs
  
  def __str__(self):
    """Renders the total elapsed time, e.g. `"125.3 s"`."""
    return "{:g} s".format(self.elapsed())
  
  def __call__(self):
    """Rerturns the elapsed time (equivalent to `elapsed()`)."""
    return self.elapsed()
  
  def reset(self):
    """Resets the total time to 0, and set the watch to stopped.
    
    The total time is returned.
    """
    t = self.stop()
    self._stored = 0.0
    self._runs = 0
    return t
  # reset()
  
  def start(self):
    """Starts the stopwatch.
    
    The watch is not reset, and a new run is started: if a run is ongoing, that
    one is stopped and a new one is started.
    To have the watch reset, use `restart()` instead.
    To have a running run not closed, use `resume()` instead.
    The time elapsed _before_ starting is returned.
    """
    # this implementation is equivalent but more precise than
    # `self.pause(); return self.resume()`
    newStartTime = self.timer()
    if self.running(): self._stored += newStartTime - self._startTime
    self._startTime = newStartTime
    self._runs += 1
    return self._stored # do not count the time elapsed by this function
  # start()
  
  def restart(self):
    """Resets and restarts the stopwatch.
    
    The time elapsed before resetting is returned.
    """
    t = self.reset()
    self.start()
    return t
  # restart()
  
  def pause(self):
    """Pauses the stopwatch, completing the current run.
    
    After calling `pause()`, the stopwatch is set in `paused()` state and the
    `partial()` time is reset to 0.
    The watch can be restarted again with `resume()`, which will initiate a new
    run (that is, `partial()` time will still start from 0).
    
    The partial elapsed time is returned, in seconds. Note that this is
    different from `stop()`, which instead returns the total elapsed time.
    
    """
    t = self.partial() # at this time the watch is effectively stopped
    self._startTime = None
    self._stored += t
    return t
  # pause()
  
  def resume(self):
    """Restarts a paused stopwatch (but it does not resets the watch).
    
    If the watch is running, no operation is performed.
    The total elapsed time is returned.
    This call does not reset the watch: if that is the desired behaviour, 
    `restart()` should be used instead.
    
    Effectively, `resume()` is equivalent to `start()`.
    """
    if self.paused():
      self._startTime = self.timer()
      self._runs += 1
    return self.elapsed()
  # resume()
  
  def partial(self):
    """Returns the time of the current run, in seconds (0 if not running)."""
    return self.timeSince(self._startTime)
  
  def elapsed(self):
    """Returns the total elapsed time, including the current and the previous
    runs, in seconds."""
    return self._stored + self.partial()
  
  def runTimeAverage(self):
    return self.elapsed() / self.runs() if self.runs() else 0.0
  
  def stop(self):
    """Stops the current run and returns the currently elapsed time."""
    self.pause()
    return self.elapsed()
  # stop()
  
  
  def toString(self, unit = "s", long_ = False, format_ = "g", options = []):
    """Returns a string rendering the current elapsed time.
    
    If `unit` is specified, that unit will be used for rendering. Supported
    units are "second", "millisecond", "microsecond" and "nanosecond" (and
    abbreviations thereof).
    """
    s = StopWatch.timeToString \
      (self.elapsed(), unit=unit, long_=long_, format_=format_)
    if options:
      optionList = []
      for option in options:
        if option == 'times':
          optionList.append("{:d} runs".format(self.runs()))
          continue
        if option == 'average':
          optionList.append("average: {}/run".format(
            StopWatch.timeToString
              (self.runTimeAverage(), unit=unit, long_=long_, format_=format_)
            ))
          continue
      # for
      if optionList: s += " (" + ", ".join(optionList) + ")"
    # if options
    return s
  # toString()
  
  
  def __enter__(self):
    """When used as context manager in a `with` statement, starts the watch.
    
    The watch is started when `with` is executed. The value bound to the `with`
    variable (after `as`) is the watch itself.
    For example:
        
        watch = StopWatch(startNow=False)
        
        with watch:
          # watch is now running
          # ...
          pass
        # watch is not running any more
        
    Note that after `with` is finished, there is no access to the partial time
    of the run within `with` scope.
    """
    self.start()
    return self
  # __enter__()
  
  def __exit__(self, exc_type, exc_value, traceback):
    """When exiting a context, the watch is paused."""
    self.pause()
  
  
  PrefixInfo = {
    'n' : { 'factor': 1.0e-9, 'long': 'nano' , 'short': 'n', },
    'u' : { 'factor': 1.0e-6, 'long': 'micro', 'short': 'u', },
    'm' : { 'factor': 1.0e-3, 'long': 'milli', 'short': 'm', },
    ''  : { 'factor': 1.0   , 'long': ''     , 'short': '' , },
    } # PrefixInfo{}
  
  @staticmethod
  def UnitName(prefix, long_):
    if not isinstance(prefix, dict): prefix = StopWatch.PrefixInfo[prefix]
    return prefix['long' if long_ else 'short'] + ('second' if long_ else 's')
  # UnitName()
  
  @staticmethod
  def timeToString(time, unit = "s", long_ = False, format_ = "g"):
    if unit:
      u = unit.lower() # fortunately we do not support capital prefixes
      if u[-1] == "s": u = u[:-1]
      if u.endswith("second"):
        long_ = True
        u = u[:-6]
      for prefixInfo in StopWatch.PrefixInfo.values():
        if u in ( prefixInfo['long'], prefixInfo['short'], ): break
      else:
        raise RuntimeError("Unknown unit: {}".format(unit))
    else:
      prefixInfo = StopWatch.PrefixInfo['']
    s = ("{:"+format_+"}").format(time / prefixInfo['factor'])
    if unit:
      s += " " + StopWatch.UnitName(prefixInfo, long_)
    return s
  # timeToString()

  
# class StopWatch


class WatchCollection:
  """A set of stopwatches.
  
  This class owns and manages the lifetime of a set of stopwatches.
  The watches are created at construction time.
  """
  def __init__(self, *watches, **kargs):
    """Initializes a set of watches.
    
    Each of the watches must be specified by a dictionary containing:
     * 'name' (mandatory): the identification of the watch, used as key
     * 'description' (optional, default: as name): a short description used in
          printout
     * 'comment' (optional): a comment used in printout
     * 'timer' (optional): use this StopWatch instead of creating a new one
     * 'startNow' (optional, default: `False`): whether to start the timer
         immediately
    
    Supported keyword arguments:
     * `title`: description of this collection
     * `namespace`: all timers are placed into the specified namespace
    """
    self.title = kargs.get('title', "")
    self.namespace = kargs.get('namespace', "")
    self.timers = []
    self.timerIndex = {}
    for wspec in watches:
      if isinstance(wspec, (str, unicode)):
        wspec = { 'name': wspec, 'description': wspec, 'comment': "", }
      self.newWatch(**wspec)
    # for specifications
  # __init__()
  
  def getTimerInfo(self, watchName):
    return self.timerIndex[self.applyNamespace(watchName)]

  def __getitem__(self, watchName): return self.getTimerInfo(watchName)['timer']
  def __iter__(self): return iter(self.timers)
  def __contains__(self, name): return name in self.timers
  
  def newWatch(self,
   name,
   description = None,
   comment = "",
   timer = None,
   startNow = False,
   namespace = None,
   ):
    if namespace is None: namespace = self.namespace
    fullName = WatchCollection.addNamespace(name, namespace)
    if fullName in self.timerIndex:
      raise RuntimeError(
        "WatchCollection['{title}']: a watch with name '{watchName}' already exists."
        .format(title=self.title, watchName=name)
        )
    newTimer = {
      'name'       : name,
      'description':
        description if description is not None else fullName, 
      'comment'    : comment,
      'namespace'  : namespace,
      'timer'      : timer if timer is not None else StopWatch(startNow=False),
      }
    self.timers.append(newTimer)
    self.timerIndex[fullName] = newTimer
    if startNow: newTimer['timer'].restart()
    return newTimer['timer']
  # newWatch()
  
  def useNamespace(self, ns): self.namespace = ns
  def applyNamespace(self, name):
    return WatchCollection.addNamespace(name, self.namespace)
  
  def withNamespace(self, namespace):
    return WatchCollection.NamespaceChanger(self, namespace)
  
  def setdefault(self, name, *args, **kargs):
    try: return self[name]
    except KeyError: return self.newWatch(name, *args, **kargs)
  # setdefault()
  
  def toAllTimers(self, action, *args, **kargs):
    for timerInfo in self.timers:
      action(timerInfo['timer'], *args, **kargs)
  # toAllTimers()
  
  def restartAll(self, *args, **kargs):
    self.toAllTimers(StopWatch.restart, *args, **kargs)
  def pauseAll(self, *args, **kargs):
    self.toAllTimers(StopWatch.pause, *args, **kargs)
  def startAll(self, *args, **kargs):
    self.toAllTimers(StopWatch.start, *args, **kargs)
  def resumeAll(self, *args, **kargs):
    self.toAllTimers(StopWatch.resume, *args, **kargs)
  def stopAll(self, *args, **kargs):
    self.toAllTimers(StopWatch.stop, *args, **kargs)
  
  def items(self): return [ ( timer['name'], timer ) for timer in self.timers ]
  def keys(self): return [ timer['name'] for timer in self.timers ]
  def values(self): return self.timers
  
  def toString(self, unit = "ms", options=()):
    s = "{}:\n".format(self.title) if self.title else ""
    return s + "\n".join([
      " * " + row
      for row in WatchCollection.formatTableRows(
      [
        [
          winfo['description'],
          winfo['timer'].toString(unit, options=options),
          winfo['comment'],
        ]
        for winfo in self.timers
      ], align=[ '<', '>', '<', ])
      ])
  # toString()
  
  def __str__(self): return self.toString()
  
  @staticmethod
  def columnFormat(data, align = "<", ):
    if isinstance(align, (str, unicode)): align = [ align, ]
    
    class StoreMax:
      def __init__(self, startValue): self.value = startValue
      def update(self, value):
        if value > self.value: self.value = value
      def __call__(self): return self.value
      def __str__(self): return str(self.value)
      def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.value)
    # StoreMax
    
    labels = [] # formatted data
    width = [] # column width
    for row in data:
      while len(row) > len(width):
        width.append(StoreMax(0))
        labels.append( [ "" ] * (len(labels[0]) if labels else 0))
      # while
      for iToken, token in enumerate(row):
        s = str(token)
        labels[iToken].append(s)
        width[iToken].update(len(s))
      # for token
    # for rows
    return [
      [
        "{s:{align}{width}}".format(
          s=token,
          width=width[iToken],
          align=align[iToken % len(align)],
          )
        for iToken, token in enumerate(row)
      ]
      for row in zip(*labels)
      ]
  # columnFormat()
  
  @staticmethod
  def formatTableRows(data, sep="  ", align="<"):
    table = WatchCollection.columnFormat(data, align=align)
    return [ sep.join(row) for row in table ]
  # formatTableRows()

  @staticmethod
  def addNamespace(name, namespace):
    return namespace + ":" + name if namespace else name
  
  
  class NamespaceChanger:
    # This enter/exit implementation is pretty bad, in that if called twice it
    # may mess things up.
    def __init__(self, coll, namespace):
      self.coll = coll
      self.oldNamespace = self.coll.namespace
      self.namespace = namespace
    def __enter__(self):
      self.coll.useNamespace(self.namespace)
      print "Namespace set:", self.coll.namespace
      return self.coll
    def __exit__(self, exc_type, exc_value, traceback):
      self.coll.useNamespace(self.oldNamespace)
      print "Namespace restored:", self.coll.namespace
  # class NamespaceChanger
  
# class WatchCollection


if __name__ == "__main__":
  
  from time import sleep
  import sys
  
  timers = WatchCollection("Timers",
    "1",
    { 'name': "2", },
    { 'name': '3', 'description': "every three", },
    { 'name': '4', 'description': "every four", 'comment': "(starts immediately)", },
    )
  
  for i in range(12):
    for name, timer in timers.items():
      try:
        if i % int(name) == 0: action = timer['timer'].start
        else:                  action = timer['timer'].stop
      except ValueError: pass
      action()
    # for
    print("{}...".format(i + 1))
    sleep(0.5)
  # for i
  timers.stopAll()
  print(timers.toString(options=('times', 'average', )))
  
  sys.exit(0)
# main
