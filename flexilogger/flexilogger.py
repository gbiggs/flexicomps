)#!/usr/bin/env python
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
from traceback import print_exc

import UI, UI__POA
import OpenRTM_aist
import RTC

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
        result.nsec = int(result.nsec - 1e9)
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
        result.nsec = int(1e9 + result.nsec)
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
    def __init__(self, mgr, abs_times=False, use_ctrl=False, ig_times=False,
            rate=0.0, file_name='', input=True, txt_mode=False, port_spec=[],
            verb=0):
        OpenRTM_aist.DataFlowComponentBase.__init__(self, mgr)

        try:
            self._abs_times = abs_times
            self._use_ctrl = use_ctrl
            self._ig_times = ig_times
            self._rate = rate
            self._file_name = file_name
            self._input = input
            self._txt_mode = txt_mode
            self._port_spec = port_spec
            self._verb = verb
            self._log_file = None
            self._next_item = None
            self._logging = False
        except:
            print_exc()
            raise

    def onInitialize(self):
        try:
            if self._use_ctrl:
                self._logging = False
                self._ctrl_impl = BasicOperationsImpl(self._start, self._stop)
                self._ctrl_port = OpenRTM_aist.CorbaPort("Control")
                self._ctrl_port.registerProvider("BasicOperations",
                        "UI.BasicOperations", self._ctrl_impl)
                self.addPort(self._ctrl_port)
            else:
                self._logging = True

            self._num_ports = 0
            self._ports = []

            self._open_log_file()
            if self._input:
                if not self._txt_mode:
                    if not self._pickle(self._port_spec):
                        print >>sys.stderr, 'Error writing port configuration.'
                        return RTC.RTC_ERROR
                port_type = OpenRTM_aist.InPort
                reg_func = self.registerInPort
                default_port_name = 'input'
            else:
                file_ports = self._read_log_item()
                if not file_ports:
                    print >>sys.stderr, 'Error reading port configuration.'
                    return RTC.RTC_ERROR
                self._port_spec = file_ports
                port_type = OpenRTM_aist.OutPort
                reg_func = self.registerOutPort
                default_port_name = 'output'

            for new_port in self._port_spec:
                if self._verb >= 3:
                    print >>sys.stderr, 'Adding port {0}'.format(new_port)
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
                self._ports.append([new_port_data, new_port_obj])
                self._num_ports += 1
                if self._verb >= 2:
                    print >>sys.stderr, 'Added port {0}'.format(new_port)
        except:
            print_exc()
            raise
        return RTC.RTC_OK

    def onActivated(self, ec_id):
        try:
            if not self._input:
                # Need to prepare the log file by reading out the first entry
                # and calculating the time offset between current computer time
                # and the time of that entry
                self._next_item = self._read_log_item()
                if self._next_item == None:
                    print >>sys.stderr, 'Error getting first item from log file'
                    return RTC.RTC_ERROR
                self._offset = subtract_times(float_to_time(time.time()),
                        self._next_item[2])
                self._next_send_time = float_to_time(time.time())
                if self._verb >= 1:
                    print >>sys.stderr, \
                            'Time offset is {0}.{1:09d}'.format(self._offset.sec,
                                    self._offset.nsec)
        except IOError, e:
            print >>sys.stderr, 'Failed to open log file {0}'.format(e)
            return RTC.RTC_ERROR
        except:
            print_exc()
            raise
        return RTC.RTC_OK

    def onDeactivated(self, ec_id):
        try:
            if self._log_file:
                self._log_file.close()
                self._log_file = None
                if self._verb >= 1:
                    print >>sys.stderr, 'Closed log file'
        except:
            print_exc()
            raise
        return RTC.RTC_OK

    def onExecute(self, ec_id):
        try:
            if self._logging:
                if self._input:
                    if not self._handle_input():
                        return RTC.RTC_ERROR
                else:
                    if not self._do_output():
                        return RTC.RTC_ERROR
        except:
            print_exc()
            raise
        return RTC.RTC_OK

    def _open_log_file(self):
        if self._input:
            flags = 'wb'
            dir = 'output'
        else:
            flags = 'rb'
            dir = 'input'
        self._log_file = open(self._file_name, flags)
        if self._verb >= 1:
            print >>sys.stderr, 'Opened log file {0} for {1}'.format(
                    self._file_name, dir)

    def _pickle(self, item):
        try:
            pickle.dump(item, self._log_file, pickle.HIGHEST_PROTOCOL)
        except pickle.PicklingError, e:
            print >>sys.stderr, 'Error pickling data: {0}'.format(e)
            return False
        return True

    def _write_log_item(self, port_num, port_type, data):
        if 'tm' in dir(data):
            data_time = data.tm
        else:
            data_time = RTC.tm
            now = time.time()
            data_time.sec = int(now)
            data_time.nsec = int(now % 1 * 1e9)
        if self._txt_mode:
            try:
                self._log_file.write('{0}\t{1}\t{2}.{3:09d}\t{4}\n'.format(
                    port_num, port_type, data_time.sec, data_time.nsec,
                    str(data)))
            except IOError, e:
                print >>sys.stderr, 'Error writing to log file: {0}'.format(e)
                return False
            return True
        else:
            return self._pickle((port_num, port_type, data_time, data))

    def _read_log_item(self):
        '''Gets the next log item from the log file and returns it unpickled as
        a tuple: (port number, port type string, data time, data)

        '''
        try:
            log_item = pickle.load(self._log_file)
        except pickle.UnpicklingError, e:
            print >>sys.stderr, 'Error unpickling data: {0}'.format(e)
            return None
        except EOFError:
            print >>sys.stderr, 'End of log file'
            return None
        return log_item

    def _handle_input(self):
        for ii in range(self._num_ports):
            if self._ports[ii][1].isNew():
                data = self._ports[ii][1].read()
                if self._verb >= 3:
                    print >>sys.stderr, \
                            'Input port {0} has new data: {1}'.format(ii,
                                    str(data))
                elif self._verb == 2:
                    print >>sys.stderr, 'Input port %d has new data.'
                if not self._write_log_item(ii, self._port_spec[ii][0], data):
                    return False
        return True

    def _do_output(self):
        if self._next_item == None:
            return False
        if self._ig_times:
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
                    self._offset)
            # Pull entries from the log and send them until the next log
            # entry's time is greater than the current time (or we run out of
            # entries)
            while self._next_item is not None and \
                    compare_times(self._next_item[2], current_time) <= 0:
                self._write_output_item(*self._next_item)
                self._next_item = self._read_log_item()
                if self._next_item == None:
                    return False
            if self._verb >= 3:
                print >>sys.stderr, \
                        'Caught up: {0}.{1:09d} < {2}.{3:09d}'.format(
                        current_time.sec, current_time.nsec,
                        self._next_item[2].sec, self._next_item[2].nsec)
        return True


    def _write_output_item(self, port_num, port_typeStr, data_time, data):
        if not self._abs_times:
            data_time = add_times(data_time, self._offset)
        self._ports[port_num][1].write(data)
        if self._verb >= 3:
            print >>sys.stderr, \
                    'Wrote log entry with time {0}.{1:09d} to port {2}: {3}'.format(
                    data_time.sec, data_time.nsec, port_num, str(data))
        elif self._verb == 2:
            print >>sys.stderr, \
                    'Wrote log entry with time {0}.{1:09d} to port {2}'.format(
                    data_time.sec, data_time.nsec, port_num, str(data))

    def _start(self):
        self._logging = True
        if self._verb >= 1:
            print >>sys.stderr, 'Logging enabled manually.'

    def _stop(self):
        self._logging = False
        if self._verb >= 1:
            print >>sys.stderr, 'Logging disabled manually.'


def find_port_type(type_name):
    types = [member for member in inspect.getmembers(RTC, inspect.isclass) \
            if member[0] == type_name]
    if len(types) == 0:
        print >>sys.stderr, \
                'Type "{0}" not found in module RTC'.format(type_name)
        return None
    elif len(types) != 1:
        print >>sys.stderr, 'Type name "{0}" is ambiguous: {1}'.format(
                type_name, str([member[0] for member in types]))
        return None
    return types[0][1]


def get_options():
    try:
        usage = 'Usage: %prog [options]\nSave data received on specified \
ports to a log file, or read data from a log file and send it over \
specified ports.'
        parser = optparse.OptionParser(usage=usage)
        parser.add_option('-a', '--absolute_times', dest='abs_times',
                action='store_true', default=False,
                help='Times from the log file are sent as absolute, rather \
than adjusted for current time. [Default: %default]')
        parser.add_option('-c', '--use_control', dest='use_control',
                action='store_true', default=False,
                help='Use a control port to enable/disable logging/playback \
when the component is active. [Default: %default]')
        parser.add_option('-g', '--ignore_times', dest='ignore_times',
                type='float', action='store', default=-1,
                help='Ignore times in the log file during playback and play \
data at the given rate in Hertz. [Defualt: %default]')
        parser.add_option('-i', '--input', dest='input', action='store_true',
                default=True,
                help='Ports are input ports, save received data to log file. \
[Default: %default]')
        parser.add_option('-l', '--logfile', dest='log_file', type='string',
                default='logger.log',
                help='Log file to write to/read from. [Default: %default]')
        parser.add_option('-n', '--port-names', dest='port_names',
                type='string', default='',
                help='Comma-separated list of port names. This list must be \
the same length as the number of ports. If no list is provided, the ports \
will be named automatically.')
        parser.add_option('-o', '--output', dest='input', action='store_false',
                help='Ports are output ports, read data from log file and \
send. Opposite of --input.')
        parser.add_option('-p', '--port', dest='ports', type='string',
                action='append', default=[],
                help='Port type. Multiple ports can be specified with \
multiple occurances of this option.')
        parser.add_option('-t', '--text', dest='text_mode',
                action='store_true', default=False,
                help='Log data in human-readable text format. WARNING: log \
files saved in this format cannot be read back in with a flexilogger in \
output mode. [Default: %default]')
        parser.add_option('-v', '--verbosity', dest='verbosity', type='int',
                default=0, help='Verbosity level (higher numbers give more \
output). [Default: %default]')
        parser.add_option('-f', dest='config_file', type='string', default='',
                help='OpenRTM option; ignored by the component.')
        options, args = parser.parse_args()
    except optparse.OptionError, e:
        print 'OptionError: ' + str(e)
        return None

    if not options.input and options.text_mode:
        parser.error('Text mode is not compatible with output mode.')
    if not options.ports and options.input:
        parser.error('Must specify at least one port')
    port_names = options.port_names.split(',')

    ports = []
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
    options.ports = ports

    if options.verbosity:
        if options.input:
            print 'Writing data from {0} ports to {1}'.format(len(ports),
                    options.log_file)
        else:
            print 'Reading data from {0} to {1} ports'.format(options.log_file,
                    len(ports))

    # Strip the options we use from sys.argv to avoid confusing the manager's
    # option parser
    sys.argv = [option for option in sys.argv \
            if option not in parser._short_opt.keys() + \
            parser._long_opt.keys() + options.ports or \
            option == '-f']
    return options


def comp_fact(opts):
    def fact_fun(mgr):
        return FlexiLogger(mgr, opts.abs_times, opts.use_control,
                opts.ignore_times != -1, 1.0 / opts.ignore_times,
                opts.log_file, opts.input, opts.text_mode, opts.ports,
                opts.verbosity)
    return fact_fun


def init(opts):
    def init_fun(mgr):
        spec = ['implementation_id',    'FlexiLogger',
            'type_name',                'FlexiLogger',
            'description',              'Flexible logging component',
            'version',                  '2.0',
            'vendor',                   'Geoffrey Biggs, AIST',
            'category',                 'DataConsumer',
            'activity_type',            'DataFlowComponent',
            'max_instance',             '999',
            'language',                 'Python',
            'lang_type',                'SCRIPT',
            '']
        profile = OpenRTM_aist.Properties(defaults_str=spec)
        mgr.registerFactory(profile, comp_fact(opts), OpenRTM_aist.Delete)
        comp = mgr.createComponent("FlexiLogger")
    return init_fun


def main():
    opts = get_options()
    if not opts:
        return 1
    mgr = OpenRTM_aist.Manager.init(len(sys.argv), sys.argv)
    mgr.setModuleInitProc(init(opts))
    mgr.activateManager()
    mgr.runManager()


if __name__ == "__main__":
    main()

