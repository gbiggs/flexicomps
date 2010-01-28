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

File: flexiconst.py

FlexiConst component.

'''

__version__ = '$Revision: $'
# $Source$

import inspect, sys
from traceback import print_exception
from time import sleep, time
from optparse import OptionParser, OptionError

import OpenRTM_aist, RTC


# Globals set by command line options
constValue = None
port = None
sleepTime = 0
verbosity = 0
flexiConstSpec = ['implementation_id', 'FlexiConst',
                  'type_name',         'FlexiConst',
                  'description',       'Produce a constant value of a \
specified type',
                  'version',           '0.0.1',
                  'vendor',            'Geoffrey Biggs, AIST',
                  'category',          'DataConsumer',
                  'activity_type',     'DataFlowComponent',
                  'max_instance',      '10',
                  'language',          'Python',
                  'lang_type',         'SCRIPT',
                  '']


class FlexiConst(OpenRTM_aist.DataFlowComponentBase):
    def __init__(self, manager):
        OpenRTM_aist.DataFlowComponentBase.__init__(self, manager)

    def onStartup(self, ec_id):
        try:
            self.__outPortData = port[1](RTC.Time(0, 0), [])
            self.__outPort = OpenRTM_aist.OutPort('output', self.__outPortData,
                                                  OpenRTM_aist.RingBuffer(8))
            self.registerOutPort('output', self.__outPort)
        except:
            print_exception(*sys.exc_info())
            return RTC.RTC_ERROR
        return RTC.RTC_OK

    def onExecute(self, ec_id):
        try:
            self.__outPortData.data = constValue
            now = time()
            self.__outPortData.tm.sec = int(now)
            self.__outPortData.tm.nsec = int((now % 1) * 1e9)
            self.__outPort.write()

            if sleepTime > 0:
                sleep(sleepTime)
        except:
            print_exception(*sys.exc_info())
        return RTC.RTC_OK


def ModuleInit(manager):
    profile = OpenRTM_aist.Properties(defaults_str = flexiConstSpec)
    manager.registerFactory(profile, FlexiConst, OpenRTM_aist.Delete)
    comp = manager.createComponent('FlexiConst')


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
    global constValue, port, sleepTime, verbosity

    try:
        usage = 'usage: %prog [options]\nProduce a constant value of a \
specified type and a specified interval.'
        parser = OptionParser(usage = usage)
        parser.add_option('-c', '--const', dest = 'const', type = 'string',
                          default = '',
                          help = 'Constant value. Must be a python expression. \
e.g. "[1,2,3]". [Default: %default]')
        parser.add_option('-p', '--port', dest = 'port', type = 'string',
                          default = '',
                          help = 'Port type. e.g. "TimedFloatSeq"')
        parser.add_option('-s', '--sleep', dest = 'sleep', type = 'float',
                          default = 0.1,
                          help = 'Time to sleep between writing the constant. \
[Default: %default]')
        parser.add_option('-v', '--verbosity', dest = 'verbosity',
                          type = 'int', default = 0,
                          help = 'Verbosity level (higher numbers give more \
output). [Default: %default]')
        options, args = parser.parse_args()
    except OptionError, e:
        print 'OptionError: ' + str(e)
        return False

    verbosity = options.verbosity

    if options.const == '':
        print 'Must provide a constant expression'
        return False
    constValue = eval(options.const)
    sleepTime = options.sleep
    if verbosity >= 2:
        print 'Constant value: ' + str(constValue)
        print 'Sleep time: ' + str(sleepTime)

    portType = FindPortType(options.port)
    if portType == None:
        return False
    port =(options.port, portType)
    if verbosity >= 2:
        print 'Output port: ' + str(port)

    # Strip the options we use from sys.argv to avoid confusing the manager's
    # option parser
    sys.argv = [option for option in sys.argv \
                if option not in parser._short_opt.keys() + \
                parser._long_opt.keys()]
    return True


def main():
    # Check options for ports
    if not GetPortOptions():
        return 1

    mgr = OpenRTM_aist.Manager.init(len(sys.argv), sys.argv)

    mgr.setModuleInitProc(ModuleInit)
    mgr.activateManager()
    mgr.runManager()
    return 0


if __name__ == "__main__":
    sys.exit(main())

