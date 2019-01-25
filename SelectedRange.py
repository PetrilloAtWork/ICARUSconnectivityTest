#!/usr/bin/env python2

__doc__ = """
Provides a simple class to parse and iterate through integral number ranges.
"""

class SelectedRange:
  """
  Class containing a range of integers.
  
  The range is the union of intervals, with bounds included.
  
  Example of usage:
      
      r = SelectedRange("5-8,11")
      assert  3 not in r
      assert  5     in r
      assert  7     in r
      assert  8     in r
      assert 10 not in r
      assert 11     in r
      assert 12 not in r
      for i in r: print i
      
  """
  
  class Range:
    def __init__(self, low, high):
      self.lower, self.upper = low, high
    def contains(self, v): return v >= self.lower and v <= self.upper
    
    @staticmethod
    def parse(spec):
      if not spec: return None
      start = 1 if spec[0] == '-' else 0
      r = spec[start:].split('-', 1)
      a = int(spec[:start] + r[0])
      b = int(r[1]) if len(r) == 2 else a
      return SelectedRange.Range(a, b)
    # parse()
    
    def begin(self): return self.lower
    def end(self): return self.upper + 1
  
    def toString(self, fmt = ''):
      return ("{:" + fmt + "}").format(self.lower) if self.lower == self.upper \
        else ("{:" + fmt + "}-{:" + fmt + "}").format(self.lower, self.upper)
    # toString()
    
    def __iter__(self): return iter(range(self.begin(), self.end()))
    def __len__(self): return max(0, self.end() - self.begin())
    
    def __contains__(self, v): return self.contains(v)
    def __str__(self): return self.toString()
    
  # class Range
  
  class Iterator:
    def __init__(self, r):
      self.rangesIter = iter(r.ranges)
      self.rangeIter = None
    def __iter__(self): return self
    def next(self):
      if not self.rangeIter:
        self.rangeIter = iter(next(self.rangesIter)) # StopIteration propagated
      try: return next(self.rangeIter)
      except StopIteration:
        self.rangeIter = None
        return next(self)
    # next()
  # class Iterator
  
  def __init__(self, spec=""):
    self.ranges = []
    if spec: self.parse(spec)
  
  def clear(self): self.ranges = []
  
  def contains(self, v):
    for r in self.ranges:
      if r.contains(v): return True
    else: return False
  # contains()
  
  def parse(self, spec):
    self.ranges = []
    for rspec in spec.split(","):
      r = SelectedRange.Range.parse(spec=rspec.strip())
      if r is not None: self.ranges.append(r)
    # for
    return self
  # parse()
  
  def toString(self, fmt = ''):
    return ",".join(r.toString(fmt=fmt) for r in self.ranges)
  
  def __iter__(self): return SelectedRange.Iterator(self)
  def __len__(self): return sum(map(len, self.ranges))
  def __contains__(self, v): return self.contains(v)
  def __str__(self): return self.toString()
  
# class SelectedRange


if __name__ == "__main__":
  import sys
  import logging
  
  testArgs = sys.argv[1:] if len(sys.argv) >= 2 else (
    ( '1,5', ( 1, 5, ) ),
    ( '1-5', range(1, 6) ),
    ( '1-3,5', ( 1, 2, 3, 5, ) ),
    ( '1-3,6, 8 - 11', ( 1, 2, 3, 6, 8, 9, 10, 11, ) ),
    ( '1-3,6, 5 - 11', ( 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, ) ),
    ( '1-3,-6,6, 5 - 11, -3 - -1', ( -6, -3, -2, -1, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, ) ),
    )
  
  checked = 0
  errors = 0
  
  for iArg, arg in enumerate(testArgs):
    spec = arg if isinstance(arg, str) else arg[0]
    solution = None if isinstance(arg, str) else arg[1]
    
    r = SelectedRange(spec=spec)
    if solution is not None:
      checked += 1
      error = False
      expected = set(solution)
      content = set(r)
      if expected != content:
        logging.error(
         "Range '{spec}' expected to contain: {expected}, got {content} instead (spurious: {{ {excess} }}; missing: {{ {deficit} }}".format(
           spec=spec,
           expected=("{ " + ", ".join(str(i) for i in solution) + " }"),
           content=str(r),
           excess=", ".join(str(i) for i in (content - expected)),
           deficit=", ".join(str(i) for i in (expected - content)),
         ))
      # if wrong content
      if error: errors += 1
    # if check
    
    print "{} => {}".format(spec, r)
    print "  contains {} elements:".format(len(r)),
    for i in range(-10, 11):
      if i in r: print i,
    print
    print "  full content:", ", ".join(map(str, r))
  else: iArg += 1
  
  if errors:
    logging.critical \
     ("{}/{} checked ranges presented errors!".format(errors, checked))
  # if errors
  
  sys.exit(0 if errors == 0 else 1)
# main
