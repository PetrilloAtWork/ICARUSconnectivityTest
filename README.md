This is a collection of scripts used at one time or another for the ICARUS connectivity test.

Setup and requirements
-----------------------

The scripts typically use National Instrument VISA and CERN ROOT.
Both should be available under python _at the same time_.
This might require a compilation of CERN ROOT from scratch.

A small `setup` script is provided, which allows to run the scripts in this repository from any directory.
A typical setup is:
    
    source ~/root/bin/this_root.sh
    source ./setup
    
To test that everything works as it should, make sure that this does not yield any error:
    
    python -c 'import ROOT, visa'
    


Data acquisition with oscilloscope
===================================

The first stage of the connectivity test happens before the regular ICARUS data acquisition system is in place.
A test box injects square waves into the detector, reads the differentiated response back, and stores the waveforms representing that response.
The fundamental scripts to interact with the oscilloscope to do that have been written by Sergi Castells.

The reading procedure is tedious enough, and `ChimneyReader` is an attempt to make it easier by wrapping Sergi's scripts and streamlining a standard test pattern (start from the highest connection down, from the lower position up).


Streamlined data acquisition session with `ChimneyReader`
----------------------------------------------------------

`ChimneyReader` is a bookkeeping object that drives through the test.
The operator interacts with it by creating an instance of it and invoking its callables directly from the python interpreter shell.
An example of the start of a data acquisition on chimney `WW04`:
```python
from testDriver import *  # make everything in `testDriver` promptly ready
reader = ChimneyReader()  # `reader` will keep track of where we are
reader.setFake()          # this is for an example only; omit this for real data acquisition
reader.start('WW04')      # declare we start a new chimney (can be done in constructor too)
reader.next()             # take the first connection + position
reader.next()             # take the second connection + position
reader.next()             # take the third connection + position; let's assume we did a mistake...
reader.removeLast()       # remove the last connection + position, prepare to take it again
reader.next()             # take the third connection + position again
#...
```
This is the output of the start of the sequence above:
```
>>> from testDriver import *  # make everything in `testDriver` promptly ready
Imported 'scope_readerB71' (as 'scope_reader')
Use `loadScopeReader(<IP address>)` to load a different one.

>>> reader = ChimneyReader()  # `reader` will keep track of where we are

>>> reader.setFake()          # this is for an example only; omit this for real data acquisition

>>> reader.start('WW04')      # declare we start a new chimney (can be done in constructor too)
readNext(): Chimney WW04 connection S18 position 1 => quickAnalysis(10, 'CHIMNEY_WW04', 'CONN_S18', 'POS_1')

>>> reader.next()             # take the first connection + position
exec quickAnalysis(10, 'CHIMNEY_WW04', 'CONN_S18', 'POS_1')
Can't plot data from 'temp_folder71/waveform_CH1_CHIMNEY_WW04_CONN_S18_POS_1_1.csv': file not found.
[...]
Can't plot data from 'temp_folder71/waveform_CH4_CHIMNEY_WW04_CONN_S18_POS_1_10.csv': file not found.
next(): Chimney WW04 connection S18 position 2 => quickAnalysis(10, 'CHIMNEY_WW04', 'CONN_S18', 'POS_2')
```
Note that both `start()` and `next()` print information about which connection and position will be tested the next time `next()` is invoked.
Some `ChimneyReader` useful callables:

* `start()`: start the data taking of a new chimney
* `next()`: data acquisition for the next connection/position in the sequence
* `printNext()`: prints which connection/position the next call to `next()` is going to process
* `removeLast()`: removes the last acquired connection/position, and sets up to aquire it again with `next()`
* `skipToNext()`, `skipToPrev()`: prepare the next position, on the previous one, to be acquired with `next()`
* `lastList()`: list (like in "returns a python list") of all data files expected to have been created in the last data acquisition
* `plotLast()`: produces plots of the last connection/position (it's also automatically done by `next()`)


Bugs
=====

`ChimneyReader`
----------------

Navigation close to the ends of the chimney connections (first connection and last position, last conection and first position) is not well protected and trouble will occur when trying to go back after finishing (e.g. if there was an error on the last position of the first connection).

