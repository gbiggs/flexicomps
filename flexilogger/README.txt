FlexiLogger
===========

A highly-flexible logging component.

Description
-----------

A logging component capable of both recording and playing back data from/to any
number of ports of any data type. The number and type of ports is controlled by
command-line options supplied when the component is executed. Playback of logged
data usually occurs at the same rate the data was received, allowing a logged
system to be simulated using this component. The playback rate can be scaled to
achieve faster or slower playback, if desired.

Requirements
------------

The component requires OpenRTM-python-1.0.0 or greater.

This component uses the new string formatting operations that were introduced
in Python 2.6. It will not function with an earlier version of Python. It has
not been tested with Python 3 and it is likely that several changes will be
necessary to make it function using this version of Python.

Input ports
-----------

Set at execution-time.

Output ports
------------

Set at execution-time.

Service ports
-------------

None.

Configuration options
---------------------

None.

Usage
-----

Execute flexilogger.py, providing a port specification. For example:
 ./flexilogger.py -p TimedInt -p TimedDoubleSeq:3 -o
Extra help is available using the --help option.

