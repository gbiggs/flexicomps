FlexiDupe
=========

Duplicate a single data stream into many data streams.

Description
-----------

This component is no longer needed in OpenRTM-1.0.0.

&br;

FlexiDupe is used to duplicate the output of a component, allowing that
component to be connected to multiple other components at the same time. This
is not possible to do directly in versions of OpenRTM prior to 1.0.

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

Execute flexidupe.py, providing a port specification. For example:
 ./flexidupe.py -p TimedDoubleSeq:3
Extra help is available using the --help option.

