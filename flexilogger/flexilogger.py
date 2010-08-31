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

FlexiLogger component.

'''

import cPickle as pickle
import inspect
import optparse
import re
import sys
import time
import traceback

import UI, UI__POA
import OpenRTM_aist
import RTC

# Globals set by command line options
absolute_times = False
ignore_control = False
ignore_times = False
playback_rate = 0
log_file_name = ''
ports_are_input = True
ports = []
verbosity = 0

def time_to_float(timeVal):
    return timeVal.sec + timeVal.nsec / 1e9


def float_to_time(floatVal):
    result = RTC.Time(0, 0)
    result.sec = int(floatVal)
    result.nsec = int((floatVal - result.sec) * 1e9)
    return result


def compare_times(t1, t2):
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


def add_times(t1, t2):
    result = RTC.Time(0, 0)
    result.sec = t1.sec + t2.sec
    result.nsec = t1.nsec + t2.nsec
    # Need to account for overflow in nanoseconds
    if result.nsec >= 1e9:
        # Should never get enough nanoseconds to make 2 seconds
        result.sec += 1
        result.nsec -= 1e9
    return result


def subtract_times(t1, t2):
    result = RTC.Time(0, 0)
    # Seconds is easy
    result.sec = t1.sec - t2.sec
    result.nsec = t1.nsec - t2.nsec
    # Need to account for overflow in nanoseconds
    if result.nsec < 0:
        # Difference in nsec can never be greater than a single second
        result.sec -= 1
        # Take the inverse number of nanoseconds, remembering that nsec is
        # negative
        result.nsec = 1e9 + result.nsec
    return result


class BasicOperationsImpl(UI__POA.BasicOperations):
    def __init__(self, start_cb, stop_cb):
        self._start_cb = start_cb
        self._stop_cb = stop_cb

    def start(self):
        self._start_cb()
        return True

    def stop(self):
        self._stop_cb()
        return True


class FlexiLogger(OpenRTM_aist.DataFlowComponentBase):
    def __init__(self, manager):
        OpenRTM_aist.DataFlowComponentBase.__init__(self, manager)
        self._log_file = None
        self._next_item = None

    def onInitialize(self):
        self._logging = False

        self._control_impl = BasicOperationsImpl(self._start, self._stop)
        self._control_port = OpenRTM_aist.CorbaPort("Control")
        self._control_port.registerProvider("BasicOperations", "UI.BasicOperations",
                self._control_impl)
        self.addPort(self._control_port)

        # Each port list is a list of tuples containing
        # (data object, port object)
        self._num_ports = 0
        self._ports = []

        if ports_are_input:
            port_type = OpenRTM_aist.InPort
            reg_func = self.registerInPort
            default_port_name = 'input'
        else:
            port_type = OpenRTM_aist.OutPort
            reg_func = self.registerOutPort
            default_port_name = 'output'

        for new_port in ports:
            if new_port[2] == '':
                port_name = default_port_name + str(self._num_ports)
            else:
                port_name = new_port[2]
            args, varargs, varkw, defaults = \
                    inspect.getargspec(new_port[1].__init__)
            if defaults:
                init_args = tuple([None \
                        for ii in range(len(args) - len(defaults) - 1)])
            else:
                init_args = [None for ii in range(len(args) - 1)]
            new_port_data = new_port[1](*init_args)
            new_port_obj = port_type(port_name, new_port_data,
                    OpenRTM_aist.RingBuffer(8))
            reg_func(port_name, new_port_obj)
            self._ports.append((new_port_data, new_port_obj))
            self._num_ports += 1
        return RTC.RTC_OK

    def onActivated(self, ec_id):
        try:
            if ports_are_input:
                self._log_file = open(log_file_name, 'wb')
                if verbosity >= 1:
                    print 'Opened log file ' + log_file_name + ' for output'
            else:
                self._log_file = open(log_file_name, 'rb')
                if verbosity >= 1:
                    print 'Opened log file ' + log_file_name + ' for input'
                # We need to prepare the log file by reading out the first entry and calculating the
                # time offset between current computer time and the time of that entry
                self._next_item = self._read_log_item()
                if self._next_item == None:
                    print 'Error getting first item from log file'
                    return RTC.RTC_ERROR
                self._time_offset = subtract_times(float_to_time(time.time()), self._next_item[2])
                self._next_send_time = float_to_time(time.time())
                if verbosity >= 1:
                    print 'Time offset is %d.%09d' % (self._time_offset.sec, self._time_offset.nsec)
        except IOError, e:
            print 'Failed to open log file: ' + str(e)
            return RTC.RTC_ERROR
        if ignore_control:
            if verbosity >= 1:
                print 'Logging enabled automatically.'
            self._logging = True
        return RTC.RTC_OK

    def onDeactivated(self, ec_id):
        if ignore_control:
            if verbosity >= 1:
                print 'Logging disabled automatically.'
            self._logging = True
        try:
            if self._log_file:
                self._log_file.close()
                self._log_file = None
                if verbosity >= 1:
                    print 'Closed log file'
        except:
            print_exception(*sys.exc_info())
        return RTC.RTC_OK

    def onExecute(self, ec_id):
        if self._logging:
            if ports_are_input:
                if not self._handle_input():
                    return RTC.RTC_ERROR
            else:
                if not self._do_output():
                    return RTC.RTC_ERROR
        return RTC.RTC_OK


    def _write_log_item(self, port_num, port_type, data_time, data):
        if text_mode:
            try:
                self._log_file.write('%s\t%s\t%d.%09d\t%s\n' % \
                        (port_num, port_type, data_time.sec,
                            data_time.nsec, str(data)))
            except IOError, e:
                print 'Error writing to log file: ' + str(e)
                return False
        else:
            try:
                pickle.dump((port_num, port_type, data_time, data),
                        self._log_file, pickle.HIGHEST_PROTOCOL)
            except pickle.PicklingError, e:
                print 'Error pickling data: ' + str(e)
                return False
        return True


    def _read_log_item(self):
        '''Gets the next log item from the log file and returns it unpickled as a tuple:
        (port number, port type string, data time, data)'''
        try:
            log_item = pickle.load(self._log_file)
        except pickle.UnpicklingError, e:
            print 'Error unpickling data: ' + str(e)
            return None
        except EOFError:
            print 'End of log file'
            return None
        return log_item


    def _handle_input(self):
        for ii in range(self._num_ports):
            if self._ports[ii][1].isNew():
                data = self._ports[ii][1].read()
                if verbosity >= 2:
                    print 'Input port %d has new data: ' % ii + str(data.data)
                if not self._write_log_item(ii, ports[ii][0], data.tm, data.data):
                    return False
        return True


    def _do_output(self):
        if self._next_item == None:
            return False
        if ignore_times:
            # Get the current time
            current_time = float_to_time(time.time())
            # If the current time is past the last send time + 1/rate, send
            # another item
            if compare_times(self._next_send_time, current_time) <= 0:
                self._write_output_item(*self._next_item)
                # Get the next item from the log file
                self._next_item = self._read_log_item()
                # Calculate the next time to send
                self._next_send_time = add_times(self._next_send_time,
                        float_to_time(playback_rate))
                if self._next_item == None:
                    return False
        else:
            # Get the current time
            current_time = subtract_times(float_to_time(time.time()),
                    self._time_offset)
            # Pull entries from the log and send them until the next log
            # entry's time is greater than the current time (or we run out of
            # entries)
            while self._next_item is not None and \
                    compare_times(self._next_item[2], current_time) <= 0:
                self._write_output_item(*self._next_item)
                self._next_item = self._read_log_item()
                if self._next_item == None:
                    return False
            if verbosity >= 3:
                print 'Caught up: %d.%09d < %d.%09d' % \
                        (current_time.sec, current_time.nsec,
                                self._next_item[2].sec,
                                self._next_item[2].nsec)
        return True


    def _write_output_item(self, port_num, port_typeStr, data_time, data):
        if not absolute_times:
            data_time = add_times(data_time, self._time_offset)
        self._ports[port_num][0].tm.sec = data_time.sec
        self._ports[port_num][0].tm.nsec = data_time.nsec
        self._ports[port_num][0].data = data
        self._ports[port_num][1].write()
        if verbosity >= 2:
            print 'Wrote log entry with time %d.%09d to port %d: %s: ' % \
                    (data_time.sec, data_time.nsec, port_num, str(data))

    def _start(self):
        self._logging = True
        if verbosity >= 1:
            print 'Logging enabled manually.'

    def _stop(self):
        self._logging = False
        if verbosity >= 1:
            print 'Logging disabled manually.'


flexilogger_spec = ['implementation_id', 'FlexiLogger',
    'type_name', 'FlexiLogger',
    'description', 'Flexible logging component',
    'version', '0.0.1',
    'vendor', 'Geoffrey Biggs, AIST',
    'category', 'DataConsumer',
    'activity_type', 'DataFlowComponent',
    'max_instance', '999',
    'language', 'Python',
    'lang_type', 'SCRIPT',
    '']


def module_init(manager):
    profile = OpenRTM_aist.Properties(defaults_str = flexilogger_spec)
    manager.registerFactory(profile, FlexiLogger, OpenRTM_aist.Delete)
    comp = manager.createComponent("FlexiLogger")


def find_port_type(typeName):
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


def get_port_options():
    global absolute_times, ignore_control, ignore_times, log_file_name, \
            playback_rate, ports_are_input, ports, text_mode, verbosity

    try:
        usage = 'usage: %prog [options]\nSave data received on specified '\
                'ports to a log file, or read data from a log file and send '\
                'it over specified ports.'
        parser = optparse.OptionParser(usage=usage)
        parser.add_option('-a', '--absolute_times', dest='abs_times',
                action='store_true', default=False,
                help='Times from the log file are sent as absolute, rather '\
                        'than adjusted for current time. [Default: %default]')
        parser.add_option('-c', '--ignore_control', dest='ignore_control',
                action='store_true', default=False,
                help='Ignore the control port and perform logging/playback '\
                        'whenever the component is active. [Default: '\
                        '%default]')
        parser.add_option('-g', '--ignore_times', dest='ignore_times',
                type='float', action='store', default=-1,
                help='Ignore times in the log file during '\
                        'playback and play data at the given rate in Hertz. '\
                        '[Defualt: %default]')
        parser.add_option('-i', '--input', dest='input', action='store_true',
                default=True,
                help='Ports are input ports, save received data to log '\
                        'file. [Default: %default]')
        parser.add_option('-l', '--logfile', dest='log_file', type='string',
                default='logger.log',
                help='Log file to write to/read from. [Default: %default]')
        parser.add_option('-n', '--port-names', dest='port_names',
                type='string', default='',
                help='Comma-separated list of port names. This list must be '\
                        'the same length as the number of ports. If no list '\
                        'is provided, the ports will be named automatically.')
        parser.add_option('-o', '--output', dest='input', action='store_false',
                help='Ports are output ports, read data from log file and '\
                        'send. Opposite of --input.')
        parser.add_option('-p', '--port', dest='ports', type='string',
                action='append', default=[],
                help='Port type. Multiple ports can be specified with '\
                        'multiple occurances of this option.')
        parser.add_option('-t', '--text', dest='text_mode',
                action='store_true', default=False,
                help='Log data in human-readable text format. WARNING: log '\
                        'files saved in this format cannot be read back in '\
                        'with a flexilogger in output mode. '\
                        '[Default: %default]')
        parser.add_option('-v', '--verbosity', dest='verbosity', type='int', default=0,
                help='Verbosity level (higher numbers give more output). '\
                        '[Default: %default]')
        parser.add_option('-f', dest='config_file', type='string', default='',
                help='OpenRTM option; ignored by the component.')
        options, args = parser.parse_args()
    except optparse.OptionError, e:
        print 'OptionError: ' + str(e)
        return False

    if len(options.ports) == 0:
        parser.error('Must specify at least one port')

    absolute_times = options.abs_times
    ignore_control = options.ignore_control
    ignore_times = options.ignore_times != -1
    playback_rate = 1.0 / options.ignore_times
    log_file_name = options.log_file
    ports_are_input = options.input
    text_mode = options.text_mode
    verbosity = options.verbosity

    port_names = options.port_names.split(',')

    for ii, port_str in zip(range(len(options.ports)), options.ports):
        port_type = find_port_type(port_str)
        if port_type == None:
            parser.error('Invalid port: ' + port_str)
        if ii < len(port_names):
            name = port_names[ii]
        else:
            name = ''
        port_info = (port_str, port_type, name)
        ports.append(port_info)
        if verbosity >= 2:
            print 'Added port: ' + str(port_info)

    if verbosity:
        if ports_are_input:
            print 'Writing data from %d ports to %s' % (len(ports), log_file_name)
        else:
            print 'Reading data from %s to %d ports' % (log_file_name, len(ports))

    # Strip the options we use from sys.argv to avoid confusing the manager's
    # option parser
    sys.argv = [option for option in sys.argv \
            if option not in parser._short_opt.keys() + \
            parser._long_opt.keys() + options.ports or \
            option == '-f']
    return True


def main():
    if not get_port_options():
        return 1

    mgr = OpenRTM_aist.Manager.init(len(sys.argv), sys.argv)
    mgr.setModuleInitProc(module_init)
    mgr.activateManager()
    mgr.runManager()

if __name__ == "__main__":
    main()

