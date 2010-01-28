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

File: flexiadd.py

FlexiAdd component.

'''

__version__ = '$Revision: $'
# $Source$

import inspect
from optparse import OptionParser, OptionError
import pickle
import re
import sys
from traceback import print_exception

import OpenRTM_aist
import RTC


# Globals set by command line options
ports = []
verbosity = 0
flexiadd_spec = ['implementation_id', 'FlexiAdd',
                'type_name',          'FlexiAdd',
                'description',        'Flexible data addition component',
                'version',            '0.0.1',
                'vendor',             'Geoffrey Biggs, AIST',
                'category',           'DataConsumer',
                'activity_type',      'DataFlowComponent',
                'max_instance',       '999',
                'language',           'Python',
                'lang_type',          'SCRIPT',
                '']


class FlexiAdd(OpenRTM_aist.DataFlowComponentBase):
    def __init__(self, manager):
        OpenRTM_aist.DataFlowComponentBase.__init__(self, manager)

    def onStartup(self, ec_id):
        try:
            # Each port list is a list of tuples containing (data object,
            # port object)
            self.__inPorts = []
            self.__inPortBuffers = []

            newPort = ports[0]
            for ii in range(newPort[2]):
                newInPortData = newPort[1](RTC.Time(0, 0), [])
                newInPort = OpenRTM_aist.InPort('input%d' % ii, newInPortData,
                                                OpenRTM_aist.RingBuffer(8))
                self.registerInPort('input%d' % ii, newInPort)
                self.__inPorts.append([newInPortData, newInPort])
                self.__inPortBuffers.append(None)

            self.__outPortData = newPort[1](RTC.Time(0, 0), [])
            self.__outPort = OpenRTM_aist.OutPort('output', self.__outPortData,
                                                  OpenRTM_aist.RingBuffer(8))
            self.registerOutPort('output', self.__outPort)
        except:
            print_exception(*sys.exc_info())
            return RTC.RTC_ERROR
        return RTC.RTC_OK

    def onExecute(self, ec_id):
        try:
            newData = False
            newTime =(0, 0)
            for ii, port in enumerate(self.__inPorts):
                if port[1].isNew():
                    newData = True
                    data = port[1].read()
                    self.__inPortBuffers[ii] = data.data
                    newTime =(data.tm.sec, data.tm.nsec)
            if newData:
                if type(self.__inPortBuffers[0]) == list:
                    result = [0 for ii in range(len(self.__inPortBuffers[0]))]
                    for ii in range(len(self.__inPortBuffers[0])):
                        for portBuffer in self.__inPortBuffers:
                            if portBuffer != None:
                                result[ii] += portBuffer[ii]
                else:
                    result = 0
                    for portBuffer in self.__inPortBuffers:
                        result += portBuffer

                self.__outPortData.data = result
                self.__outPortData.tm.sec = newTime[0]
                self.__outPortData.tm.nsec = newTime[1]
                self.__outPort.write()
        except:
            print_exception(*sys.exc_info())
        return RTC.RTC_OK


def MyModuleInit(manager):
    profile = OpenRTM_aist.Properties(defaults_str = flexiadd_spec)
    manager.registerFactory(profile, FlexiAdd, OpenRTM_aist.Delete)
    comp = manager.createComponent("FlexiAdd")


def FindPortType(typeName):
    types = [member for member in inspect.getmembers(RTC, inspect.isclass) \
             if member[0] == typeName]
    if len(types) == 0:
        print 'Type "' + typeName + '" not found in module RTC'
        return None
    elif len(types) != 1:
        print 'Type name "' + typeName + '" is ambiguous: ' + \
                str([member[0] for member in types])
        return None
    return types[0][1]


def GetPortOptions():
    global ports, verbosity

    try:
        usage = 'usage: %prog [options]\nAdd multiple data streams together \
to produce a single output.'
        parser = OptionParser(usage = usage)
        parser.add_option('-p', '--port', dest = 'ports', type = 'string',
                          action = 'append', default = [],
                          help = 'Port type and number of times to add. e.g. \
"TimedFloatSeq:4"')
        parser.add_option('-v', '--verbosity', dest = 'verbosity',
                          type = 'int', default = 0,
                          help = 'Verbosity level (higher numbers give more \
output). [Default: %default]')
        options, args = parser.parse_args()
    except OptionError, e:
        print 'OptionError: ' + str(e)
        return False

    if len(options.ports) == 0:
        parser.error('Must specify at least one port')

    verbosity = options.verbosity

    for portStr in options.ports:
        fields = portStr.split(':')
        if len(fields) > 2:
            parser.error('Invalid port type.number format: %s' % portStr)
            return False
        portType = FindPortType(fields[0])
        if portType == None:
            return False
        portInfo =(fields[0], portType, int(fields[1]))
        ports.append(portInfo)
        if verbosity >= 2:
            print 'Added port: ' + str(portInfo)

    # Strip the options we use from sys.argv to avoid confusing the
    # manager's option parser
    sys.argv = [option for option in sys.argv \
                if option not in parser._short_opt.keys() + \
                parser._long_opt.keys()]
    return True


def main():
    # Check options for ports
    if not GetPortOptions():
        return 1

    mgr = OpenRTM_aist.Manager.init(len(sys.argv), sys.argv)

    mgr.setModuleInitProc(MyModuleInit)
    mgr.activateManager()
    mgr.runManager()
    return 0


if __name__ == "__main__":
    sys.exit(main())

