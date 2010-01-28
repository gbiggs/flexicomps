FlexiDump
=========

Dump data streams to stdout with varying levels of verbosity.

Description
-----------

FlexiDump is an extremely useful component. It can be used to watch the
contents of any data stream. If you are unsure if a component is outputting the
correct data, or even outputting data at all, FlexiDump is the tool you need.
Create a FlexiDump instance with the correct input port types and connect it to
the output ports you want to check. There is no need to alter the running
system, or to modify existing components.

Requirements
------------

The component require OpenRTM-python-1.0.0 or greater.

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

Execute flexidump.py, providing a port specification. For example:
 ./flexidump.py -p TimedDouble -v 1
 ./flexidump.py -p TimedDoubleSeq -v 2
Extra help is available using the --help option.

