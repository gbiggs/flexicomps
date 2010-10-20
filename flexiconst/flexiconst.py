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

FlexiConst component.

'''


import imp
import inspect
import sys
from traceback import print_exc
from time import time
from optparse import OptionParser, OptionError

import OpenRTM_aist
import RTC


class FlexiConst(OpenRTM_aist.DataFlowComponentBase):
    def __init__(self, mgr, const, port, mods, verb=0):
        OpenRTM_aist.DataFlowComponentBase.__init__(self, mgr)
        self._const = const
        self._port = port
        self._mods = mods
        self._verb = verb

    def onInitialize(self):
        try:
            args, varargs, varkw, defaults = \
                    inspect.getargspec(self._port[1].__init__)
            if defaults:
                init_args = tuple([None \
                        for ii in range(len(args) - len(defaults) - 1)])
            else:
                init_args = [None for ii in range(len(args) - 1)]
            self._out_data = self._port[1](*init_args)
            self._outport = OpenRTM_aist.OutPort('output', self._out_data,
                    OpenRTM_aist.RingBuffer(8))
            self.registerOutPort('output', self._outport)
        except:
            print_exc()
            return RTC.RTC_ERROR
        return RTC.RTC_OK

    def onExecute(self, ec_id):
        try:
            if 'tm' in dir(self._out_data):
                now = time()
                self._out_data.tm = RTC.Time(int(now), int((now % 1) * 1e9))
                if 'data' in dir(self._out_data):
                    self._out_data.data = self._const
                self._outport.write()
            else:
                self._outport.write(self._const)
        except:
            print_exc()
            return RTC.RTC_ERROR
        return RTC.RTC_OK


def import_user_mod(mod_name):
    f = None
    m = None
    try:
        f, p, d = imp.find_module(mod_name)
        m = imp.load_module(mod_name, f, p, d)
    except ImportError, e:
        print >>sys.stderr, '{0}: {1}: Error importing module: {2}'.format(\
                sys.argv[0], mod_name, e)
        m = None
    finally:
        if f:
            f.close()
    if not m:
        return None
    return (mod_name, m)


def import_user_mods(mod_names):
    all_mod_names = []
    for mn in mod_names.split(','):
        if not mn:
            continue
        all_mod_names += [mn, mn + '__POA']
    mods = [import_user_mod(mn) for mn in all_mod_names]
    if None in mods:
        return None
    return mods


def find_port_type(type_name, modules):
    for (mn, m) in modules:
        types = [member for member in inspect.getmembers(m, inspect.isclass) \
                 if member[0] == type_name]
        if len(types) == 0:
            continue
        elif len(types) != 1:
            print 'Type name "{0}" is ambiguous: {1}'.format(type_name,
                    str([member[0] for member in types]))
            return None
        else:
            return types[0][1]
    print >>sys.stderr, 'Type "{0}" not found'.format(type_name)
    return None


def get_options():
    try:
        usage = 'usage: %prog [options]\nProduce a constant value of a \
specified type and a specified interval.'
        parser = OptionParser(usage = usage)
        parser.add_option('-c', '--const', dest = 'const', type = 'string',
                          default = '',
                          help = 'Constant value. Must be a python expression. \
e.g. "[1,2,3]". [Default: %default]')
        parser.add_option('-m', '--type-mod', dest='type_mods', action='store',
                type='string', default='',
                help='Specify the module containing the data type. This \
option must be supplied if the data type is not defined in the RTC modules \
supplied with OpenRTM-aist. This module and the __POA module will both be \
imported.')
        parser.add_option('-p', '--port', dest = 'port', type = 'string',
                          default = '',
                          help = 'Port type. e.g. "TimedFloatSeq"')
        parser.add_option('-r', '--rate', dest = 'rate', type = 'float',
                          default = 1.0,
                          help = 'Rate in Hertz to emit the constant. \
[Default: %default]')
        parser.add_option('-v', '--verbosity', dest = 'verbosity',
                          type = 'int', default = 0,
                          help = 'Verbosity level (higher numbers give more \
output). [Default: %default]')
        options, args = parser.parse_args()
    except OptionError, e:
        print 'OptionError: ' + str(e)
        return None, None, None

    if options.const == '':
        print '{0}: Must provide a constant expression'.format(sys.argv[0])
        return None, None, None

    user_mods = import_user_mods(options.type_mods)
    if user_mods is None:
        return None, None, None
    mods = user_mods + [('RTC', RTC)]
    port_type = find_port_type(options.port, mods)
    if port_type == None:
        return None, None, None
    port = (options.port, port_type)
    if options.verbosity >= 2:
        print 'Rate: {0}\nOutput port: {1}'.format(options.rate, port)

    # Strip the options we use from sys.argv to avoid confusing the manager's
    # option parser
    sys.argv = [option for option in sys.argv \
                if option not in parser._short_opt.keys() + \
                parser._long_opt.keys()]
    return options, port, mods


def replace_mod_name(string, mods):
    for (mn, m) in mods:
        if mn in string:
            string = string.replace(mn, 'mods[{0}][1]'.format(mods.index((mn, m))))
    return string


def eval_const(const_expr, mods):
    try:
        repl_const_expr = replace_mod_name(const_expr, mods)
        if not repl_const_expr:
            return None
        const = eval(repl_const_expr)
    except:
        print_exc()
        return None
    return const


def comp_fact(opts, port, mods):
    def fact_fun(mgr):
        const = eval_const(opts.const, mods)
        if not const:
            return None
        return FlexiConst(mgr, const, port, mods, opts.verbosity)
    return fact_fun


def init(opts, port, mods):
    def init_fun(mgr):
        spec = ['implementation_id',    'FlexiConst',
            'type_name',                'FlexiConst',
            'description',              'Flexible constant-producing component',
            'version',                  '3.0',
            'vendor',                   'Geoffrey Biggs, AIST',
            'category',                 'DataProducer',
            'activity_type',            'DataFlowComponent',
            'max_instance',             '999',
            'language',                 'Python',
            'lang_type',                'SCRIPT',
            'exec_cxt.periodic.type',   'PeriodicExecutionContext',
            'exec_cxt.periodic.rate',   '{0}'.format(opts.rate),
            '']
        profile = OpenRTM_aist.Properties(defaults_str=spec)
        mgr.registerFactory(profile, comp_fact(opts, port, mods),
                OpenRTM_aist.Delete)
        comp = mgr.createComponent("FlexiConst")
    return init_fun


def main():
    opts, port, mods = get_options()
    if not opts:
        return 1
    mgr = OpenRTM_aist.Manager.init(len(sys.argv), sys.argv)
    mgr.setModuleInitProc(init(opts, port, mods))
    mgr.activateManager()
    mgr.runManager()
    return 0


if __name__ == "__main__":
    sys.exit(main())

