FlexiFilter
===========

A flexible data reorganising and transforming component.

Description
-----------

This component filters data received on its input ports and transmits it on its
output ports. The filtering process allows for reorganisation of the received
data. Data transformations are automatically performed as necessary, allowing
any data type to be mapped to any other data type. For example, 3 input ports,
each of which receives a pair of floating-point numbers, can be reorganised so
that one number from each port goes to an output port emitting three
floating-point numbers, while the other number from each port is redirected to
its own output port emitting a single integer number.

Data scaling by a scale factor before and after reorganisation is also supported.

The number and type of ports is controlled by command-line options supplied
when the component is executed.

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

Execute flexifilter.py, providing a port specification. For example,
 ./flexifilter.py -i TimedFloatSeq:2 -i TimedString -i TimedLong -o TimedStringSeq:4 -o TimedFloat -m "2>0:2,0:1>0.1>0:3,0:1>1"
This will produce a filter as shown in diagram.png.

Extra help is available using the --help option.

