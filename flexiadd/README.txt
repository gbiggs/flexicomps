FlexiAdd
========

Add multiple data streams together to produce a single output.

Description
-----------

This component is used to add multiple data streams, typically output by
different components. The result is output as a single data stream. An example
use case for this component is implementing a motor schemas-based control
scheme. The number and type of input ports is controlled by command line
options supplied when the component is executed.

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

Execute flexiadd.py, providing a port specification. For example:
 ./flexiadd.py -p TimedDouble:3
 ./flexiadd.py -p TimedIntSeq:5
Extra help is available using the --help option.

