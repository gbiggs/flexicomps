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

File: flexidupe.py

FlexiDupe component.

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

flexidump_spec = ['implementation_id',        'FlexiDupe',
                'type_name',                'FlexiDupe',
                'description',                "Flexible data duplication component (for those times when it doesn't work like it should)",
                'version',                    '0.0.1',
                'vendor',                    'Geoffrey Biggs, AIST',
                'category',                    'DataConsumer',
                'activity_type',            'DataFlowComponent',
                'max_instance',                '999',
                'language',                    'Python',
                'lang_type',                'SCRIPT',
                '']

class FlexiDupe (OpenRTM_aist.DataFlowComponentBase):
    def __init__ (self, manager):
        OpenRTM_aist.DataFlowComponentBase.__init__ (self, manager)


    def onStartup (self, ec_id):
        try:
            # Each port list is a list of tuples containing (data object, port object)
            self.__numPorts = 0
            self.__inPorts = []
            self.__outPorts = []

            for newPort in ports:
                newPortData = newPort[1] (RTC.Time (0, 0), [])
                newPortPort = OpenRTM_aist.InPort ('input%d' % self.__numPorts, newPortData, OpenRTM_aist.RingBuffer (8))
                self.registerInPort ('input%d' % self.__numPorts, newPortPort)
                self.__inPorts.append ((newPortData, newPortPort))

                newOutPorts = []
                for ii in range (newPort[2]):
                    newOutPortData = newPort[1] (RTC.Time (0, 0), [])
                    newOutPort = OpenRTM_aist.OutPort ('output%d_%d' % (self.__numPorts, ii), newOutPortData, OpenRTM_aist.RingBuffer (8))
                    self.registerOutPort ('output%d_%d' % (self.__numPorts, ii), newOutPort)
                    newOutPorts.append ((newOutPortData, newOutPort))
                self.__outPorts.append (newOutPorts)

                self.__numPorts += 1
        except:
            print_exception (*sys.exc_info ())
            return RTC.RTC_ERROR
        return RTC.RTC_OK


    def onExecute (self, ec_id):
        try:
            for ii in range (self.__numPorts):
                if self.__inPorts[ii][1].isNew ():
                    data = self.__inPorts[ii][1].read ()
                    for outPort in self.__outPorts[ii]:
                        outPort[0].data = data.data
                        outPort[0].tm.sec = data.tm.sec
                        outPort[0].tm.nsec = data.tm.nsec
                        outPort[1].write ()
        except:
            print_exception (*sys.exc_info ())
        return RTC.RTC_OK


def MyModuleInit (manager):
    profile = OpenRTM_aist.Properties (defaults_str = flexidump_spec)
    manager.registerFactory (profile, FlexiDupe, OpenRTM_aist.Delete)
    comp = manager.createComponent ("FlexiDupe")


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
        usage = 'usage: %prog [options]\nDuplicate a single data stream into \
many data streams.'
        parser = OptionParser (usage = usage)
        parser.add_option ('-p', '--port', dest = 'ports', type = 'string', action = 'append', default = [],
                            help = 'Port type and number of times to duplicate. Multiple ports can '\
                            'be specified with multiple occurrences of this option. e.g. "TimedFloatSeq:4"')
        parser.add_option ('-v', '--verbosity', dest = 'verbosity', type = 'int', default = 0,
                            help = 'Verbosity level (higher numbers give more output). [Default: %default]')
        parser.add_option ('-f', dest = 'configfile', type = 'string', default = '',
                            help = 'OpenRTM_aist option; ignored by the component.')
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
    sys.argv = [option for option in sys.argv if option not in parser._short_opt.keys () + parser._long_opt.keys () + options.ports or option == '-f']
    return True


def main ():
    # Check options for ports
    if not GetPortOptions ():
        return 1

    mgr = OpenRTM_aist.Manager.init (len (sys.argv), sys.argv)

    mgr.setModuleInitProc (MyModuleInit)
    mgr.activateManager ()
    mgr.runManager ()

if __name__ == "__main__":
    main ()
