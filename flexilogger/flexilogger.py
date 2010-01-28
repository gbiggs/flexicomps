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

File: flexilogger.py

FlexiLogger component.

'''

__version__ = '$Revision: $'
# $Source$

import cPickle as pickle, inspect, re, sys, time
from traceback import print_exception
from optparse import OptionParser, OptionError

import OpenRTM_aist, RTC

# Globals set by command line options
absoluteTimes = False
ignoreTimes = False
playbackRate = 0
logFileName = ''
portsAreInput = True
ports = []
verbosity = 0

flexilogger_spec = ['implementation_id',        'FlexiLogger',
                    'type_name',                'FlexiLogger',
                    'description',                'Flexible logging component',
                    'version',                    '0.0.1',
                    'vendor',                    'Geoffrey Biggs, AIST',
                    'category',                    'DataConsumer',
                    'activity_type',            'DataFlowComponent',
                    'max_instance',                '999',
                    'language',                    'Python',
                    'lang_type',                'SCRIPT',
                    '']


def TimetoFloat (timeVal):
    return timeVal.sec + timeVal.nsec / 1000000000.0


def FloatToTime (floatVal):
    result = RTC.Time (0, 0)
    result.sec = int (floatVal)
    result.nsec = int ((floatVal - result.sec) * 1000000000.0)
    return result


def CompTimes (t1, t2):
    if t1.sec < t2.sec:
        return -1
    elif t1.sec > t2.sec:
        return 1
    elif t1.sec == t2.sec:
        if t1.nsec < t2.nsec:
            return -1
        elif t1.nsec > t2.nsec:
            return 1
        else:
            return 0


def AddTimes (t1, t2):
    result = RTC.Time (0, 0)
    result.sec = t1.sec + t2.sec
    result.nsec = t1.nsec + t2.nsec
    # Need to account for overflow in nanoseconds
    if result.nsec >= 1000000000:
        # Should never get enough nanoseconds to make 2 seconds
        result.sec += 1
        result.nsec -= 1000000000
    return result


def SubtractTimes (t1, t2):
    result = RTC.Time (0, 0)
    # Seconds is easy
    result.sec = t1.sec - t2.sec
    result.nsec = t1.nsec - t2.nsec
    # Need to account for overflow in nanoseconds
    if result.nsec < 0:
        # Difference in nsec can never be greater than a single second
        result.sec -= 1
        # Take the inverse number of nanoseconds, remembering that nsec is negative
        result.nsec = 1000000000 + result.nsec
    return result


class FlexiLogger (OpenRTM_aist.DataFlowComponentBase):
    def __init__ (self, manager):
        OpenRTM_aist.DataFlowComponentBase.__init__ (self, manager)
        self.__logFile = None
        self.__nextItem = None


    def onStartup (self, ec_id):
        try:
            # Each port list is a list of tuples containing (data object, port object)
            self.__numPorts = 0
            self.__ports = []

            if portsAreInput:
                rtmPortType = OpenRTM_aist.InPort
                registerFunc = self.registerInPort
                portNameStr = 'input'
            else:
                rtmPortType = OpenRTM_aist.OutPort
                registerFunc = self.registerOutPort
                portNameStr = 'output'

            for newPort in ports:
                newPortData = newPort[1] (RTC.Time (0, 0), [])
                newPortPort = rtmPortType (portNameStr + str (self.__numPorts), newPortData, OpenRTM_aist.RingBuffer (8))
                registerFunc (portNameStr + str (self.__numPorts), newPortPort)
                self.__ports.append ((newPortData, newPortPort))
                self.__numPorts += 1
        except:
            print_exception (*sys.exc_info ())
            return RTC.RTC_ERROR
        return RTC.RTC_OK


    def onActivated (self, ec_id):
        # Open the log file
        try:
            if portsAreInput:
                self.__logFile = open (logFileName, 'wb')
                if verbosity >= 1:
                    print 'Opened log file ' + logFileName + ' for output'
            else:
                self.__logFile = open (logFileName, 'rb')
                if verbosity >= 1:
                    print 'Opened log file ' + logFileName + ' for input'
                # We need to prepare the log file by reading out the first entry and calculating the
                # time offset between current computer time and the time of that entry
                self.__nextItem = self.readLogItem ()
                if self.__nextItem == None:
                    print 'Error getting first item from log file'
                    return RTC.RTC_ERROR
                self.__timeOffset = SubtractTimes (FloatToTime (time.time ()), self.__nextItem[2])
                self.__nextSendTime = FloatToTime(time.time())
                if verbosity >= 1:
                    print 'Time offset is %d.%09d' % (self.__timeOffset.sec, self.__timeOffset.nsec)
        except IOError, e:
            print 'Failed to open log file: ' + str (e)
            return RTC.RTC_ERROR
        except:
            print_exception (*sys.exc_info ())
            return RTC.RTC_ERROR
        return RTC.RTC_OK


    def onDeactivated (self, ec_id):
        try:
            if self.__logFile:
                self.__logFile.close ()
                self.__logFile = None
                if verbosity >= 1:
                    print 'Closed log file'
        except:
            print_exception (*sys.exc_info ())
        return RTC.RTC_OK


    def onExecute (self, ec_id):
        try:
            if portsAreInput:
                if not self.HandleInput ():
                    return RTC.RTC_ERROR
            else:
                if not self.DoOutput ():
                    return RTC.RTC_ERROR
        except:
            print_exception (*sys.exc_info ())
        return RTC.RTC_OK


    def writeLogItem (self, portNum, portType, dataTime, data):
        if textMode:
            try:
                self.__logFile.write ('%s\t%s\t%d.%09d\t%s\n' % (portNum, portType, dataTime.sec, dataTime.nsec, str (data)))
            except IOError, e:
                print 'Error writing to log file: ' + str (e)
                return False
        else:
            try:
                pickle.dump ((portNum, portType, dataTime, data), self.__logFile, pickle.HIGHEST_PROTOCOL)
            except pickle.PicklingError, e:
                print 'Error pickling data: ' + str (e)
                return False
        return True


    def readLogItem (self):
        '''Gets the next log item from the log file and returns it unpickled as a tuple:
        (port number, port type string, data time, data)'''
        try:
            logItem = pickle.load (self.__logFile)
        except pickle.UnpicklingError, e:
            print 'Error unpickling data: ' + str (e)
            return None
        except EOFError:
            print 'End of log file'
            return None
        return logItem


    def HandleInput (self):
        for ii in range (self.__numPorts):
            if self.__ports[ii][1].isNew ():
                data = self.__ports[ii][1].read ()
                if verbosity >= 2:
                    print 'Input port %d has new data: ' % ii + str (data.data)
                if not self.writeLogItem (ii, ports[ii][0], data.tm, data.data):
                    return False
        return True


    def DoOutput (self):
        if self.__nextItem == None:
            return False
        if ignoreTimes:
            # Get the current time
            currentTime = FloatToTime (time.time ())
            # If the current time is past the last send time + 1/rate, send
            # another item
            if CompTimes (self.__nextSendTime, currentTime) <= 0:
                self.WriteOutputItem (*self.__nextItem)
                # Get the next item from the log file
                self.__nextItem = self.readLogItem ()
                # Calculate the next time to send
                self.__nextSendTime = AddTimes(self.__nextSendTime,
                                               FloatToTime(playbackRate))
                if self.__nextItem == None:
                    return False
        else:
            # Get the current time
            currentTime = SubtractTimes (FloatToTime (time.time ()), self.__timeOffset)
            # Pull entries from the log and send them until the next log entry's time is greater than
            # the current time (or we run out of entries)
            while self.__nextItem is not None and CompTimes (self.__nextItem[2], currentTime) <= 0:
                self.WriteOutputItem (*self.__nextItem)
                # Get the next item from the log file
                self.__nextItem = self.readLogItem ()
                if self.__nextItem == None:
                    return False
            if verbosity >= 3:
                print 'Caught up: %d.%09d < %d.%09d' % (currentTime.sec, currentTime.nsec, self.__nextItem[2].sec, self.__nextItem[2].nsec)
        return True


    def WriteOutputItem (self, portNum, portTypeStr, dataTime, data):
        if not absoluteTimes:
            dataTime = AddTimes (dataTime, self.__timeOffset)
        self.__ports[portNum][0].tm.sec = dataTime.sec
        self.__ports[portNum][0].tm.nsec = dataTime.nsec
        self.__ports[portNum][0].data = data
        self.__ports[portNum][1].write ()
        if verbosity >= 2:
            print 'Wrote log entry with time %d.%09d to port %d: %s: ' % (dataTime.sec, dataTime.nsec, portNum, str (data))


def MyModuleInit (manager):
    profile = OpenRTM_aist.Properties (defaults_str = flexilogger_spec)
    manager.registerFactory (profile, FlexiLogger, OpenRTM_aist.Delete)
    comp = manager.createComponent ("FlexiLogger")


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
    global absoluteTimes, ignoreTimes, logFileName, playbackRate, portsAreInput, ports, textMode, verbosity

    try:
        usage = 'usage: %prog [options]\nSave data received on specified ports to a log file, or read data from a log file and send it over specified ports.'
        parser = OptionParser (usage=usage)
        parser.add_option ('-a', '--absolute_times', dest='absTimes', action='store_true', default=False,
                            help='Times from the log file are sent as absolute, rather than adjusted for current time. [Default: %default]')
        parser.add_option ('-g', '--ignore_times', dest='ignoreTimes',
                           type='float', action='store', default=-1,
                           help='Ignore times in the log file during playback \
and play data at the given rate in Hertz. [Defualt: %default]')
        parser.add_option ('-i', '--input', dest='input', action='store_true', default=True,
                            help='Ports are input ports, save received data to log file. [Default: %default]')
        parser.add_option ('-l', '--logfile', dest='logFile', type='string', default='logger.log',
                            help='Log file to write to/read from. [Default: %default]')
        parser.add_option ('-o', '--output', dest='input', action='store_false',
                            help='Ports are output ports, read data from log file and send. Opposite of --input.')
        parser.add_option ('-p', '--port', dest='ports', type='string', action='append', default=[],
                            help='Port type. Multiple ports can be specified with multiple occurances of this option.')
        parser.add_option ('-t', '--text', dest='textMode', action='store_true', default=False,
                            help='Log data in human-readable text format. WARNING: log files saved in this format '\
                            'cannot be read back in with a flexilogger in output mode. [Default: %default]')
        parser.add_option ('-v', '--verbosity', dest='verbosity', type='int', default=0,
                            help='Verbosity level (higher numbers give more output). [Default: %default]')
        parser.add_option ('-f', dest='configfile', type='string', default='',
                            help='OpenRTM option; ignored by the component.')
        options, args = parser.parse_args ()
    except OptionError, e:
        print 'OptionError: ' + str (e)
        return False

    if len (options.ports) == 0:
        parser.error ('Must specify at least one port')

    absoluteTimes = options.absTimes
    ignoreTimes = options.ignoreTimes != -1
    playbackRate = 1.0 / options.ignoreTimes
    logFileName = options.logFile
    portsAreInput = options.input
    textMode = options.textMode
    verbosity = options.verbosity

    for portStr in options.ports:
        portType = FindPortType (portStr)
        if portType == None:
            parser.error ('Invalid port: ' + portStr)
        portInfo = (portStr, portType)
        ports.append (portInfo)
        if verbosity >= 2:
            print 'Added port: ' + str (portInfo)

    if verbosity:
        if portsAreInput:
            print 'Writing data from %d ports to %s' % (len (ports), logFileName)
        else:
            print 'Reading data from %s to %d ports' % (logFileName, len (ports))

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
