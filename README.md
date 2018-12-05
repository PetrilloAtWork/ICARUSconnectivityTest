This is a collection of scripts used at one time or another for the ICARUS connectivity test.

Setup and requirements
-----------------------

The scripts have been tested with python version 2.7.15.

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

`ChimneyReader` is a bookkeeping object that drives through the test.
The operator interacts with it by creating an instance of it and invoking its callables directly from the python interpreter shell.
From version 4, this object _requires_ a configuration file (or more).

An example of the start of a data acquisition on chimney `A04`:
```python
from testDriver import ChimneyReader # make `ChimneyReader` available
reader = ChimneyReader(              # create a `ChimneyReader` object
  [                                  # configured with two configuration files:
    "config/TDS3054C-base.ini",           # a basic setting one,
    "config/TDS3054C-192.168.230.29.ini", # and one overriding the `scope IP address
  ],
  fake=True                          # for this example, we don't connect to the `scope
  )
reader.start("A04")                 # declare we start a new chimney (can be done in constructor too)
reader.next()                        # take the first connection + position
reader.next()                        # take the second connection + position
reader.next()                        # take the third connection + position; let's assume we did a mistake...
reader.removeLast()                  # remove the last connection + position, prepare to take it again
reader.next()                        # take the third connection + position again
#...
```
This is the output of the start of the sequence above:
    
    Python 2.7.15 (default, May 21 2018, 17:53:03) [GCC] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    >>> from testDriver import ChimneyReader # make `ChimneyReader` available
    >>> reader = ChimneyReader(              # create a `ChimneyReader` object
    ...   [                                  # configured with two configuration files:
    ...     "config/TDS3054C-base.ini",           # a basic setting one,
    ...     "config/TDS3054C-192.168.230.29.ini", # and one overriding the `scope IP address
    ...   ],
    ...   fake=True                          # for this example, we don't connect to the `scope
    ...   )
    INFO:root:Configuration file: 'config/TDS3054C-base.ini'
    INFO:root:Configuration file: 'config/TDS3054C-192.168.230.29.ini'
    >>> reader.start("A04")                 # declare we start a new chimney (can be done in constructor too)
    INFO:root:Output for this chimney will be written into: 'CHIMNEY_A04_inprogress'
    INFO:root:next(): Test pulse chimney A04 connection V01 position 1
    INFO:root:Hint:
    * remove pulser and ribbon cables and switch the board to slot 1
    * direct test box pulser output to the pulse input for V01
      => test all the different pulse inputs to find the best one
    * plug the left signal ribbon into the test box
    * turn to position 1
    >>> reader.next()                        # take the first connection + position
    INFO:root:Written 10000 points into 'CHIMNEY_A04_inprogress/PULSEwaveform_CH1_CHIMNEY_A04_CONN_V01_POS_1_1.csv'
    INFO:root:Written 10000 points into 'CHIMNEY_A04_inprogress/PULSEwaveform_CH2_CHIMNEY_A04_CONN_V01_POS_1_1.csv'
    [...]
    INFO:root:Written 10000 points into 'CHIMNEY_A04_inprogress/PULSEwaveform_CH3_CHIMNEY_A04_CONN_V01_POS_1_10.csv'
    INFO:root:Written 10000 points into 'CHIMNEY_A04_inprogress/PULSEwaveform_CH4_CHIMNEY_A04_CONN_V01_POS_1_10.csv'
    Rendering: CH1.......... CH2.......... CH3.......... CH4.......... done.
    INFO:root:next(): Test pulse chimney A04 connection V01 position 2
    INFO:root:Hint:
    * just turn to position 2
    True
    >>> reader.next()                        # take the second connection + position
    INFO:root:Written 10000 points into 'CHIMNEY_A04_inprogress/PULSEwaveform_CH1_CHIMNEY_A04_CONN_V01_POS_2_11.csv'
    INFO:root:Written 10000 points into 'CHIMNEY_A04_inprogress/PULSEwaveform_CH2_CHIMNEY_A04_CONN_V01_POS_2_11.csv'
    [...]
    INFO:root:Written 10000 points into 'CHIMNEY_A04_inprogress/PULSEwaveform_CH3_CHIMNEY_A04_CONN_V01_POS_2_20.csv'
    INFO:root:Written 10000 points into 'CHIMNEY_A04_inprogress/PULSEwaveform_CH4_CHIMNEY_A04_CONN_V01_POS_2_20.csv'
    Rendering: CH1.......... CH2.......... CH3.......... CH4.......... done.
    INFO:root:next(): Test pulse chimney A04 connection V01 position 3
    INFO:root:Hint:
    * just turn to position 3
    True
    >>> reader.next()                        # take the third connection + position; let's assume we did a mistake...
    INFO:root:Written 10000 points into 'CHIMNEY_A04_inprogress/PULSEwaveform_CH1_CHIMNEY_A04_CONN_V01_POS_3_21.csv'
    INFO:root:Written 10000 points into 'CHIMNEY_A04_inprogress/PULSEwaveform_CH2_CHIMNEY_A04_CONN_V01_POS_3_21.csv'
    [...]
    INFO:root:Written 10000 points into 'CHIMNEY_A04_inprogress/PULSEwaveform_CH3_CHIMNEY_A04_CONN_V01_POS_3_30.csv'
    INFO:root:Written 10000 points into 'CHIMNEY_A04_inprogress/PULSEwaveform_CH4_CHIMNEY_A04_CONN_V01_POS_3_30.csv'
    Rendering: CH1.......... CH2.......... CH3.......... CH4.......... done.
    INFO:root:next(): Test pulse chimney A04 connection V01 position 4
    INFO:root:Hint:
    * just turn to position 4
    True
    >>> reader.removeLast()                  # remove the last connection + position, prepare to take it again
    Remove 40 files from Test PULSE chimney A04 connection V01 position 3? [Y/N] y
    INFO:root:next(): Test pulse chimney A04 connection V01 position 3
    INFO:root:Hint:
    * just turn to position 3

    True
    >>> reader.next()                        # take the third connection + position again
    INFO:root:Written 10000 points into 'CHIMNEY_A04_inprogress/PULSEwaveform_CH1_CHIMNEY_A04_CONN_V01_POS_3_21.csv'
    INFO:root:Written 10000 points into 'CHIMNEY_A04_inprogress/PULSEwaveform_CH2_CHIMNEY_A04_CONN_V01_POS_3_21.csv'
    [...]
    INFO:root:Written 10000 points into 'CHIMNEY_A04_inprogress/PULSEwaveform_CH3_CHIMNEY_A04_CONN_V01_POS_3_30.csv'
    INFO:root:Written 10000 points into 'CHIMNEY_A04_inprogress/PULSEwaveform_CH4_CHIMNEY_A04_CONN_V01_POS_3_30.csv'
    Rendering: CH1.......... CH2.......... CH3.......... CH4.......... done.
    INFO:root:next(): Test pulse chimney A04 connection V01 position 4
    INFO:root:Hint:
    * just turn to position 4
    True
    
Note that both `start()` and `next()` print information about which connection and position will be tested the next time `next()` is invoked.
By default, hints on the actions to perform next are also printed on screen.

Some `ChimneyReader` useful callables:

* `start()`: start the data taking of a new chimney
* `next()`: data acquisition for the next connection/position in the sequence
* `printNext()`: prints which connection/position the next call to `next()` is going to process
* `removeLast()`: removes the last acquired connection/position, and sets up to aquire it again with `next()`
* `skipToNext()`, `skipToPrev()`: prepare the next position, on the previous one, to be acquired with `next()`
* `jumpTo(cable, position, test)`: jump directly to the specified cable, position and test
* `lastList()`: list (like in "returns a python list") of all data files expected to have been created in the last data acquisition
* `plotLast()`: produces plots of the last connection/position (it's also automatically done by `next()`)
* `verify()`: verifies the acquired data
* `generateArchivalScript()`: generates the script to archive the acquired data


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


December 2018 configurations
=============================

The following command line can be used as first entry in a python shell to
initialise the data taking for the chimney specified in `start()` (in the
example, `A0`, which is not a real chimney):

| test type      | oscilloscope | command                                                                                                                         |
| -------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| bias only      | scope1       | `from testDriver import ChimneyReader ; reader = ChimneyReader("config/FlangeWorkbenchTestHV_scope1.ini"); reader.start("A0")`  |
| bias and wires | scope1       | `from testDriver import ChimneyReader ; reader = ChimneyReader("config/FlangeChimneyTest_scope1.ini"); reader.start("A0")`      |
| bias only      | scope2       | `from testDriver import ChimneyReader ; reader = ChimneyReader("config/FlangeWorkbenchTestHV_scope2.ini"); reader.start("A0")`  |
| bias and wires | scope2       | `from testDriver import ChimneyReader ; reader = ChimneyReader("config/FlangeChimneyTest_scope2.ini"); reader.start("A0")`      |


Bugs
=====

`ChimneyReader`
----------------

_None known so far._



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
