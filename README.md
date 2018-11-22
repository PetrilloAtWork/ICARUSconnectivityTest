This is a collection of scripts used at one time or another for the ICARUS connectivity test.

Setup and requirements
-----------------------

The scripts typically use National Instrument VISA and CERN ROOT.
Both should be available under python _at the same time_.
This might require a compilation of CERN ROOT from scratch.
In appendix, there is some report of success in installing the required software in a Linux distribution.

A small `setup` script is provided, which allows to run the scripts in this repository from any directory.
A typical setup is:
    
    source ~/root/bin/this_root.sh
    source ./setup
    
To test that everything works as it should, make sure that this does not yield any error:
    
    python -c 'import ROOT, visa'
    
A (local) network connection needs to be established between the node (say, laptop) and the oscilloscope.
To test the communication, try:
    
    import visa
    manager = visa.ResourceManager()
    scope = manager.open_resource('TCPIP0::192.168.230.29::INSTR')
    print(scope.query("*IDN?"))
    
which in my case prints:
    
    TEKTRONIX,TDS 3054C,0,CF:91.1CT FV:v4.05 TDS3FFT:v1.00 TDS3TRG:v1.00
    
    
(this means success!)


Data acquisition with oscilloscope
===================================

The first stage of the connectivity test happens before the regular ICARUS data acquisition system is in place.
A test box injects square waves into the detector, reads the differentiated response back, and stores the waveforms representing that response.
The fundamental scripts to interact with the oscilloscope to do that have been written by Sergi Castells.

The reading procedure is tedious enough, and `ChimneyReader` is an attempt to make it easier by wrapping Sergi's scripts and streamlining a standard test pattern (start from the highest connection down, from the lower position up).


Streamlined data acquisition session with `ChimneyReader`
----------------------------------------------------------

**This procedure needs to be updated with version 2.0 of the software!**

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


Verification and archival of data files
----------------------------------------

Once all the channels of a chimney have been recorded, the data needs to be
transferred to a publicly available area.
The following two steps are strongly recommended:

1. verify that all the files are effectively there, and that there is no
   corruption in the data
2. archive the data

The `ChimneyReader` object provides a function `verify()` to perform the
verification at a good degree, up to verifying that each file is legible and
with the right format and amount of information.
The object does _not_ provide a service to archive the files, mostly because
that is a job that should happen asynchronously. It _does_ provide a script that
can be run to perform the archival, though. The standard procedure is to
generate the script, and then run it on a different shell. Do this only after
verification has succeeded!
    
    reader.verify()
    reader.generateArchivalScript()
    
The first step, verification, can take 5 minutes on a machine with a _fast_
disk. This should be less time than it is needed to wrap up and set up the next
chimney, so that should be fine. But if the verification takes too long, it can
be simplified by decreasing its thoroughness, that is literally by running
`reader.verify(thoroughness=3)` (which does not try to see if it is numbers that
are stored into the CSV files) or `reader.verify(thoroughness=2)` (which does
not even check that the files have the expected number of points, and that is
fast beyond any excuse).
If the verification succeeds, `verify()` will rename the output directory
marking it as not "in progress" any more, and making the CSV files read-only.
It will also create a small text file with some metadata of the acquisition.
It is on the renamed directory that `generateArchivalScript()` works. The script
always attempts to archive all the (5760) files that it knows _should_ be
there, and if some of them are not there, the ones present will be archived,
the others will produce error messages, and the script will exit with a non-zero
status. Rerunning the script will not copy again the files that were already
successfully archived.



Bugs
=====

`ChimneyReader`
----------------

Navigation close to the ends of the chimney connections (first connection and last position, last connection and first position) is not well protected and trouble will occur when trying to go back after finishing (e.g. if there was an error on the last position of the first connection).



Appendix: installing oscilloscope interface under Linux OS
===========================================================

The installation of the required interface to the oscilloscope includes two components:

1. National Instruments drivers ("VISA")
2. python interface to the oscilloscope (via the drivers)


Installing National Instrument VISA drivers
--------------------------------------------

Instructions on installing National Instrument VISA drivers in Linux OS are at http://www.ni.com/product-documentation/54754/en.
They work for selected Linux distributions, all RPM-based. The idea is that you download the location of additional software repositories from National Instruments, and install from them with the native package manage of your Linux distribution.

Effectively what I did for OpenSUSE was:
* download the "driver" package (from http://www.ni.com/download/ni-linux-device-drivers-2018/7664/en); on early November 2018, I ended up downloading drivers from October 2018
* unzip the file, and ask my distribution to install the proper RPM (`sudo zypper install ./rpm_OpenSUSE423.rpm`)
* open openSUSE package manager interface (from YaST2); a new National Instrument repository is listed _and enabled_ already
* selected the NI VISA runtime, development package and documentation (probably selecting the metapackage `ni-visa` will do, and overdo as well);
  a number of packages lacked checksum verification (meaning the reference checksum was not found): I chose to _ignore_ the problem
* 200 MB later, we are set to go.

More-or-less useful links:

* [NIVISA](https://www.ni.com/visa): introduction to what NI-VISA is and is for


Installing the python interface
--------------------------------

Documentation on the Python interface can be found on [PyVISA][GitHub].
The recommended approach is to install the interface via `pip`: `pip install pyvisa`.
In my distribution (openSUSE), `pip` is in fact the Python 3 version of it, and I had to make sure I was using `pip2` instead:
    
    pip2 install --user pyvisa
    
I also requested the package to be installed in my user area rather than system-wide. If installing on a system you manage with multiple users, then you might want to install it system-wide instead (`sudo pip2 install pyvisa`).

It is not clear to me if the oscilloscope needs to be listed in `/etc/ni-visa/visaconf.ini`.
I ended up adding it via `visaconf` executable, which required some LabView packages to be installed, which in openSUSE was a problem since they had no checksum.
But this is what it ended up adding to the configuration file:

    [TCPIP-RSRCS]
    SynchronizeAllSocket=0
    SynchronizeAllVxi11=1
    NumOfResources=1
    Name0="TCPIP0::192.168.230.29::INSTR"
    Enabled0=1
    Static0=1

    [ALIASES]
    Alias0="'SLAC-borrowed-TDS3054C','TCPIP0::192.168.230.29::INSTR'"
    NumAliases=1

where `192.168.230.29` is the address I assigned to the oscilloscope.


[NIVISA]: https://www.ni.com/visa
[PyVISA]: https://github.com/pyvisa/pyvisa
