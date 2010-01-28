FlexiConst
==========

Produce a constant value of a specified type and a specified interval.

Description
-----------

FlexiConst provides a data stream of a constant value. The data type and value
to output are specified on the command line at execution time. The data type
can be any valid Python expression, such as a floating-point number or a list
of values. The time between each output of the constant can be controlled.

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

Execute flexiconst.py, providing a port specification. For example:

 # Outputs 6.2 every 0.5s
 ./flexiconst.py -p TimedDouble -c 6.2 -s 0.5
 # Outputs every 10s
 ./flexiconst.py -p TimedIntSeq -c "[1,2,3]" -s 10

Extra help is available using the --help option.

