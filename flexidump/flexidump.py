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

FlexiDump component.

'''


import imp
import inspect
import optparse
import sys
import traceback

import OpenRTM_aist
import RTC


class FlexiDump (OpenRTM_aist.DataFlowComponentBase):
    def __init__ (self, mgr, port_spec, verb=0):
        OpenRTM_aist.DataFlowComponentBase.__init__ (self, mgr)
        self._port_spec = port_spec
        self._verb = verb

    def onInitialize (self):
        try:
            self._num_ports = 0
            self._ports = []

            for new_port in self._port_spec:
                if self._verb >= 3:
                    print >>sys.stderr, 'Adding port {0}'.format(new_port)
                if new_port[2] == '':
                    port_name = 'input' + str(self._num_ports)
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
                new_port_obj = OpenRTM_aist.InPort(port_name, new_port_data,
                        OpenRTM_aist.RingBuffer(8))
                self.registerInPort(port_name, new_port_obj)
                self._ports.append([new_port_data, new_port_obj])
                self._num_ports += 1
                if self._verb >= 2:
                    print >>sys.stderr, 'Added port {0}'.format(new_port)
        except:
            traceback.print_exc()
            return RTC.RTC_ERROR
        return RTC.RTC_OK

    def onExecute(self, ec_id):
        try:
            for p in self._ports:
                if p[1].isNew():
                    data = p[1].read()
                    if self._verb == -1:
                        print 'Input port {0} has new data'.format(p[0])
                    else:
                        print 'Input port {0} has new data: {1}'.format(p[0],
                                data)
        except:
            traceback.print_exc()
        return RTC.RTC_OK


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
        usage = 'Usage: %prog [options]\nDump data streams to standard out.'
        parser = optparse.OptionParser(usage=usage)
        parser.add_option('-n', '--port-names', dest='port_names',
                type='string', default='',
                help='Comma-separated list of port names. This list must be \
the same length as the number of ports. If no list is provided, the ports \
will be named automatically.')
        parser.add_option('-p', '--port', dest='ports', type='string',
                action='append', default=[],
                help='Port type. Multiple ports can be specified with \
multiple occurances of this option.')
        parser.add_option('-v', '--verbosity', dest='verbosity', type='int',
                default=0, help='Verbosity level (higher numbers give more \
output). [Default: %default]')
        options, args = parser.parse_args()
    except optparse.OptionError, e:
        print 'OptionError: ' + str(e)
        return None

    if not options.ports:
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
        print 'Reading data from {0} ports'.format(len(ports))

    # Strip the options we use from sys.argv to avoid confusing the manager's
    # option parser
    sys.argv = [option for option in sys.argv \
            if option not in parser._short_opt.keys() + \
            parser._long_opt.keys() + options.ports or \
            option == '-f']
    return options


def comp_fact(opts):
    def fact_fun(mgr):
        return FlexiDump(mgr, opts.ports, opts.verbosity)
    return fact_fun


def init(opts):
    def init_fun(mgr):
        spec = ['implementation_id',    'FlexiDump',
            'type_name',                'FlexiDump',
            'description',              'Flexible dumping component',
            'version',                  '3.0',
            'vendor',                   'Geoffrey Biggs, AIST',
            'category',                 'DataConsumer',
            'activity_type',            'DataFlowComponent',
            'max_instance',             '999',
            'language',                 'Python',
            'lang_type',                'SCRIPT',
            '']
        profile = OpenRTM_aist.Properties(defaults_str=spec)
        mgr.registerFactory(profile, comp_fact(opts), OpenRTM_aist.Delete)
        comp = mgr.createComponent("FlexiDump")
    return init_fun


def main():
    opts = get_options()
    if not opts:
        return 1
    mgr = OpenRTM_aist.Manager.init(len(sys.argv), sys.argv)
    mgr.setModuleInitProc(init(opts))
    mgr.activateManager()
    mgr.runManager()
    return 0


if __name__ == "__main__":
    main()

