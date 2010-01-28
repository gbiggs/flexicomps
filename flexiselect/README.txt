FlexiSelect
===========

Select one data stream from many based on the value of another data stream.

Description
-----------

The FlexiSelect component provides selection between two or more data streams
of the same type based on another data stream. An example use case is to select
between two robot controller components based on the output of a GUI component
or the output of a manager component. The multiple data streams are chosen
between and the single chosen stream is output.

&br;

The selection port is of type TimedShort. It is the zero-based index of the
input data stream to use.

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

Execute flexiselect.py, providing a port specification. For example:
 ./flexiselect.py -p TimedDoubleSeq3
Extra help is available using the --help option.

