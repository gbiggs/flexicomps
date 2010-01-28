#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''flexicomps

Copyright (C) 2008-2010
    Geoffrey Biggs
    RT-Synthesis Research Group
    Intelligent Systems Research Institute,
    National Institute of Advanced Industrial Science and Technology (AIST),
    Japan
    All rights reserved.
Licensed under the Eclipse Public License -v 1.0 (EPL)
http://www.opensource.org/licenses/eclipse-1.0.txt

File: flexiselect.py

FlexiSelect component.

'''

__version__ = '$Revision: $'
# $Source$

import inspect, pickle, re, sys
from traceback import print_exception
from optparse import OptionParser, OptionError

import OpenRTM_aist, RTC

# Globals set by command line options
ports = []
verbosity = 0

flexiselect_spec = ['implementation_id',        'FlexiSelect',
                    'type_name',                'FlexiSelect',
                    'description',                "Flexible input selection component",
                    'version',                    '0.0.1',
                    'vendor',                    'Geoffrey Biggs, AIST',
                    'category',                    'DataConsumer',
                    'activity_type',            'DataFlowComponent',
                    'max_instance',                '999',
                    'language',                    'Python',
                    'lang_type',                'SCRIPT',
                    '']

class FlexiSelect (OpenRTM_aist.DataFlowComponentBase):
    def __init__ (self, manager):
        OpenRTM_aist.DataFlowComponentBase.__init__ (self, manager)

        self.__selection = RTC.TimedShort (RTC.Time (0, 0), 0)
        self.__selectionIn = OpenRTM_aist.InPort ('selection', self.__selection, OpenRTM_aist.RingBuffer (8))
        self.registerInPort ('selection', self.__selectionIn)


    def onStartup (self, ec_id):
        try:
            self.__selection.data = 0

            # Each port list is a list of tuples containing (data object, port object)
            self.__inPorts = []
            self.__inPortBuffers = []

            newPort = ports[0]
            for ii in range (newPort[2]):
                newInPortData = newPort[1] (RTC.Time (0, 0), [])
                newInPort = OpenRTM_aist.InPort ('input%d' % ii, newInPortData, OpenRTM_aist.RingBuffer (8))
                self.registerInPort ('input%d' % ii, newInPort)
                self.__inPorts.append ([newInPortData, newInPort])

            self.__outPortData = newPort[1] (RTC.Time (0, 0), [])
            self.__outPort = OpenRTM_aist.OutPort ('output', self.__outPortData, OpenRTM_aist.RingBuffer (8))
            self.registerOutPort ('output', self.__outPort)
        except:
            print_exception (*sys.exc_info ())
            return RTC.RTC_ERROR
        return RTC.RTC_OK


    def onExecute (self, ec_id):
        try:
            if self.__selectionIn.isNew ():
                self.__selection = self.__selectionIn.read ()
                if self.__selection.data > len (self.__inPorts) - 1:
                    print 'Index %d is out of range (%d inputs)' % (self.__selection.data, len (self.__inPorts))
                    return RTC.RTC_ERROR
                print 'Selected port %d' % self.__selection.data

            inputPort = self.__inPorts[self.__selection.data]
            if inputPort[1].isNew ():
                inputPort[0] = inputPort[1].read ()
                self.__outPortData.tm.sec = inputPort[0].tm.sec
                self.__outPortData.tm.nsec = inputPort[0].tm.nsec
                self.__outPortData.data = inputPort[0].data
                self.__outPort.write ()
        except:
            print_exception (*sys.exc_info ())
        return RTC.RTC_OK


def ModuleInit (manager):
    profile = OpenRTM_aist.Properties (defaults_str = flexiselect_spec)
    manager.registerFactory (profile, FlexiSelect, OpenRTM_aist.Delete)
    comp = manager.createComponent ("FlexiSelect")


def FindPortType (typeName):
    types = [member for member in inspect.getmembers (RTC, inspect.isclass) if member[0] == typeName]
    if len (types) == 0:
        print 'Type "' + typeName + '" not found in module RTC'
        return None
    elif len (types) != 1:
        print 'Type name "' + typeName + '" is ambiguous: ' + str ([member[0] for member in types])
        return None
    return types[0][1]


def GetPortOptions ():
    global ports, verbosity

    try:
        usage = 'usage: %prog [options]\nSelect one data stream from many \
based on the value of another data stream.'
        parser = OptionParser (usage = usage)
        parser.add_option ('-p', '--port', dest = 'ports', type = 'string', action = 'append', default = [],
                            help = 'Port type and number of occurances of it. e.g. "TimedFloatSeq:4"')
        parser.add_option ('-v', '--verbosity', dest = 'verbosity', type = 'int', default = 0,
                            help = 'Verbosity level (higher numbers give more output). [Default: %default]')
        options, args = parser.parse_args ()
    except OptionError, e:
        print 'OptionError: ' + str (e)
        return False

    if len (options.ports) == 0:
        parser.error ('Must specify at least one port')

    verbosity = options.verbosity

    for portStr in options.ports:
        fields = portStr.split (':')
        if len (fields) > 2:
            parser.error ('Invalid port type.number format: %s' % portStr)
            return False
        portType = FindPortType (fields[0])
        if portType == None:
            return False
        portInfo = (fields[0], portType, int (fields[1]))
        ports.append (portInfo)
        if verbosity >= 2:
            print 'Added port: ' + str (portInfo)

    # Strip the options we use from sys.argv to avoid confusing the manager's option parser
    sys.argv = [option for option in sys.argv if option not in parser._short_opt.keys () + parser._long_opt.keys ()]
    return True


def main ():
    # Check options for ports
    if not GetPortOptions ():
        return 1
    mgr = OpenRTM_aist.Manager.init (len (sys.argv), sys.argv)
    mgr.setModuleInitProc (ModuleInit)
    mgr.activateManager ()
    mgr.runManager ()

if __name__ == "__main__":
    main ()
