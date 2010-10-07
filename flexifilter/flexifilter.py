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

File: flexifilter.py

FlexiFilter component.

'''

__version__ = '$Revision: $'
# $Source$

import inspect, re, sys
from traceback import print_exception
from optparse import OptionParser, OptionError

import OpenRTM_aist, RTC

from typemap import typeMap, multMap

#Globals set by command line options
inputPorts = []
outputPorts = []
newestTime = False
verbosity = 0
zeroOld = False


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


# Class to store a pin mapping
class PinMapping:
	def __init__ (self, port, pin, multiplier = None, postMult = False, convFunc = None):
		self.port = port				# Index into the inputPorts list for this pin's source
		self.pin = pin					# Pin number on the input port for this pin's source
		self.multiplier = multiplier	# None for no multiplier
		self.postMult = postMult		# False to pre-multiply
		self.convFunc = convFunc		# None for no conversion function


	def ConvertData (self, data):
		# Check if conversion is needed
		if self.convFunc is None:
			if self.multiplier is not None:
				# No conversion, but have a multiplier
				return data * self.multiplier
			else:
				# No conversion, no multiplier
				return data
		else:
			# Have conversion
			outputData = data
			if self.multiplier is not None and not self.postMult:
				# Pre-multiply
				outputData *= self.multiplier
			# Convert the data
			outputData = self.convFunc (outputData)
			if self.multiplier is not None and self.postMult:
				# Post-multiply
				outputData *= self.multiplier
			return outputData


# Structure to store a port
class Port:
	def __init__ (self, desc, index, type, length, emptyVal):
		self.desc = desc			# The string from the command line for this port
		self.index = index			# Port number
		self.type = type			# Port type object
		self.length = length		# Port length (must be 0 for non-sequence ports)
		self.emptyVal = emptyVal	# Value when no data
		self.data = None			# Data storage for the port (set later)
		self.portObj = None			# The actual port object (set later)

		# Source(s) for this port (initialised now, possibly set later)
		if self.length == 0:
			# Scalar ports have None or a PinMapping object
			self.sourceMap = None
		else:
			# This list contains one PinMapping for each pin on the port, or None for no input to that pin.
			self.sourceMap = [None for ii in range (self.length)]

		# Data received times for this port (set later)
		if self.length == 0:
			self.times = None		# No need to store a history of received times for a scalar
		else:
			self.times = [RTC.Time (0, 0) for ii in range (self.length)]


	def GetDataTime (self):
		if self.length == 0:
			return self.data.tm
		times = self.times
		times.sort (cmp = CompTimes)
		if newestTime:
			return times[-1]
		else:
			return times[0]


flexifilter_spec = ['implementation_id',	'FlexiFilter',
		 'type_name',					'FlexiFilter',
		 'description',					'Flexible filter',
		 'version',						'0.0.1',
		 'vendor',						'Geoffrey Biggs, AIST',
		 'category',					'DataConsumer',
		 'activity_type',				'DataFlowComponent',
		 'max_instance',				'999',
		 'language',					'Python',
		 'lang_type',					'SCRIPT',
		 '']


class FlexiFilter (OpenRTM_aist.DataFlowComponentBase):
	def __init__ (self, manager):
		OpenRTM_aist.DataFlowComponentBase.__init__ (self, manager)
		self.__inputPorts = inputPorts
		self.__outputPorts = outputPorts


	def onStartup (self, ec_id):
		try:
			# Each port list is a list of tuples containing (data object, port object)
			self.__numInputPorts = len (self.__inputPorts)
			self.__numOutputPorts = len (self.__outputPorts)

			for newPort in self.__inputPorts:
				newPortData = newPort.type (RTC.Time (0, 0), [])
				newPortPort = OpenRTM_aist.InPort ('input%d' % newPort.index, newPortData, OpenRTM_aist.RingBuffer (8))
				self.registerInPort ('input%d' % newPort.index, newPortPort)
				newPort.data = newPortData
				newPort.portObj = newPortPort

			for newPort in self.__outputPorts:
				newPortData = newPort.type (RTC.Time (0, 0), [newPort.emptyVal for ii in range (newPort.length)])
				newPortPort = OpenRTM_aist.OutPort ('output%d' % newPort.index, newPortData, OpenRTM_aist.RingBuffer (8))
				self.registerOutPort ('output%d' % newPort.index, newPortPort)
				newPort.data = newPortData
				newPort.portObj = newPortPort
		except:
			print_exception (*sys.exc_info ())
			return RTC.RTC_ERROR
		return RTC.RTC_OK


	def onActivated (self, ec_id):
		for port in self.__outputPorts:
			# Clear out old data
			if port.length != 0:
				port.data.data = [port.emptyVal for kk in range (port.length)]
			else:
				port.data.data = port.emptyVal
		return RTC.RTC_OK


	def onExecute (self, ec_id):
		try:
			haveNewData = False
			inputData = []

			outputPortIsNew = [False for ii in range (self.__numOutputPorts)]
			for port in self.__inputPorts:
				if port.portObj.isNew ():
					inputData.append (port.portObj.read ())
					haveNewData = True
					if verbosity >= 2:
						print 'Input port %d has new data: ' % port.index + str (inputData[-1].data)
				else:
					inputData.append (None)		# No data for this port
			if not haveNewData:
				return RTC.RTC_OK

			# For each pin on each output port, check if its input has new data and convert as appropriate
			for port in self.__outputPorts:
				if zeroOld:
					# Clear out old data (this will only be written if there is new data for this port available)
					if port.length != 0:
						port.data.data = [port.emptyVal for kk in range (port.length)]
					else:
						port.data.data = port.emptyVal
				if port.length == 0:		# Scalar port
					if port.sourceMap is None:
						continue		# No input for this pin
					if inputData[port.sourceMap.port] is None:
						continue		# No new data for this pin
					if self.__inputPorts[port.sourceMap.port].length == 0:
						newData = inputData[port.sourceMap.port].data
					else:
						newData = inputData[port.sourceMap.port].data[port.sourceMap.pin]
					# Copy the (possibly converted) data to the output port and mark the port as new
					port.data.data = port.sourceMap.ConvertData (newData)
					port.data.tm = inputData[port.sourceMap.port].tm
					outputPortIsNew[port.index] = True
				else:
					for ii in range (port.length):
						if port.sourceMap[ii] is None:
							continue	# No input for this pin
						sourceMap = port.sourceMap[ii]
						if inputData[sourceMap.port] is None:
							continue	# No new data for this pin
						if self.__inputPorts[sourceMap.port].length == 0:
							newData = inputData[sourceMap.port].data
						else:
							newData = inputData[sourceMap.port].data[sourceMap.pin]
						# Copy the (possibly converted) data to the output port and mark the port as new
						port.data.data[ii] = sourceMap.ConvertData (newData)
						port.times[ii] = inputData[sourceMap.port].tm
						port.data.tm = port.GetDataTime ()
						outputPortIsNew[port.index] = True
			# Write each output port that has new data
			for ii in range (self.__numOutputPorts):
				if outputPortIsNew[ii]:
					if verbosity >= 2:
						print 'Output port %d has new data: ' % ii + str (self.__outputPorts[ii].data.data)
					self.__outputPorts[ii].portObj.write ()
		except:
			print_exception (*sys.exc_info ())
		return RTC.RTC_OK


def FlexiFilterInit (manager):
	profile = OpenRTM_aist.Properties (defaults_str = flexifilter_spec)
	manager.registerFactory (profile, FlexiFilter, OpenRTM_aist.Delete)
	comp = manager.createComponent ("FlexiFilter")


def FindPortType (typeName):
	types = [member for member in inspect.getmembers (RTC, inspect.isclass) if member[0] == typeName]
	if len (types) == 0:
		print 'Type "' + typeName + '" not found in module RTC'
		return None
	elif len (types) != 1:
		print 'Type name "' + typeName + '" is ambiguous: ' + str ([member[0] for member in types])
		return None
	return types[0][1]


def GetConversionFunction (inputType, outputType):
	if outputType not in typeMap:
		print 'Unknown output type: ' + outputType
		return None
	convFunc = typeMap[outputType][0]
	postMultiply = multMap[inputType][outputType]
	if postMultiply == -1:
		print 'Cannot multiply these data types: ' + inputType + ', ' + outputType
		return None
	return convFunc, postMultiply


def PrintMap (ports):
	for port in ports:

		print 'Port ' + str (port.index)
		if port.length == 0:
			print 'Scalar:',
			if port.sourceMap == None:
				print '-'
			else:
				if port.sourceMap.multiplier != None:
					multStr = '\tMultiplier: ' + str (port.sourceMap.multiplier)
					if port.sourceMap.postMult:
						multStr += ' (Post-multiplied)'
					else:
						multStr += ' (Pre-multiplied)'
				else:
					multStr = ''
				if port.sourceMap.convFunc == None:
					convStr = 'No conversion'
				else:
					convStr = str (port.sourceMap.convFunc)
				print 'Input: %d:%d\tType: ' % (port.sourceMap.port, port.sourceMap.pin) + convStr + multStr
		else:
			for jj in range (len (port.sourceMap)):
				print 'Pin %d:' % jj,
				pinMap = port.sourceMap[jj]
				if pinMap == None:
					print '-'
				else:
					if pinMap.multiplier != None:
						multStr = '\tMultiplier: ' + str (pinMap.multiplier)
						if pinMap.postMult:
							multStr += ' (Post-multiplied)'
						else:
							multStr += ' (Pre-multiplied)'
					else:
						multStr = ''
					if pinMap.convFunc == None:
						convStr = 'No conversion'
					else:
						convStr = str (pinMap.convFunc)
					print 'Input: %d:%d\tType: ' % (pinMap.port, pinMap.pin) + convStr + multStr


def DecodePortStr (portStr):
	portInfo = portStr.rsplit (':')
	if len (portInfo) == 1:
		portTypeStr = portInfo[0]
		portLengthStr = 0
	else:
		portTypeStr = portInfo[0]
		portLengthStr = portInfo[1]
	portType = FindPortType (portTypeStr)

	if portType == None:
		return None
	if portTypeStr not in typeMap:
		print 'Unknown port type: ' + portTypeStr
		return None

	try:
		portLength = int (portLengthStr)
	except ValueError:
		print 'Invalid port length: ' + portLengthStr
		return None

	# Sanity check on the port length
	if portLength == 0:
		if portTypeStr.endswith ('Seq'):
			print 'Sequence port type has length of zero: ' + portStr
			return None
	else:
		if not portTypeStr.endswith ('Seq'):
			print 'Non-sequence port type has non-zero length: ' + portStr
			return None
	return Port (portStr, 0, portType, portLength, typeMap[portTypeStr][1])


def GetPortOptions ():
	global inputPorts, outputPorts, newestTime, verbosity, zeroOld

	try:
		usage = 'usage: %prog [options]\nMap input ports to output ports, with multipliers and type conversion.'
		parser = OptionParser (usage = usage)
		parser.add_option ('-i', '--inputport', dest = 'inputport', type = 'string', action = 'append', default = [],
							help = 'Input port specification in the format "type[:length]". Length is necessary for sequence ports.')
		parser.add_option ('-m', '--map', dest = 'mapping', type = 'string', default = '0>0',
							help = 'Mapping from input elements to output elements. [Default: %default]\n'\
							'Port/pin mappings are specified as a comma-separated list of number pairs with optional '\
							'multipliers and pin numbers. Unspecified pins default to 0. '\
							'For example, "2>0:2,0:1>0.1>0:3,0:1>1" will map input port 2 pin '\
							'0 to output port 0 pin 2, input port 0 pin 1 to output port 0 pin 3 with a multiplier of '\
							'0.1, and input port 0 pin 1 to output port 1 pin 0.')
		parser.add_option ('-n', '--newesttime', dest = 'newestTime', action = 'store_true', default = False,
							help = 'Use the time of the most recent data for an output port\'s time, rather than the time of '\
							'the oldest data used on the port. Only applies to sequence ports. [Default: %default]')
		parser.add_option ('-o', '--outputport', dest = 'outputport', type = 'string', action = 'append', default = [],
							help = 'Output port specification in the format "type[:length]". Length is necessary for sequence ports.')
		parser.add_option ('-v', '--verbosity', dest = 'verbosity', type = 'int', default = 0,
							help = 'Verbosity level (higher numbers give more output). [Default: %default]')
		parser.add_option ('-z', '--zeroold', dest = 'zeroOld', action = 'store_true', default = False,
							help = 'If new data is not available on one of the source ports for an output, pins connected to that port '\
							'are set to zero (or equivalent) when other pins are updated. Otherwise, they remain at their previous '\
							'value. Only applies to sequence ports. [Default: %default]')
		options, args = parser.parse_args ()
	except OptionError, e:
		print 'OptionError: ' + str (e)
		return False

	newestTime = options.newestTime
	zeroOld = options.zeroOld

	if len (options.inputport) == 0:
		parser.error ('Must specify at least one input port.')
	if len (options.outputport) == 0:
		parser.error ('Must specify at least one input port.')

	portCount = 0
	for portStr in options.inputport:
		portInfo = DecodePortStr (portStr)
		if portInfo == None:
			parser.error ('Invalid port: ' + portStr)
		portInfo.index = portCount
		inputPorts.append (portInfo)
		if verbosity >= 2:
			print 'Added input port: ' + str (portInfo)
		portCount += 1

	portCount = 0
	for portStr in options.outputport:
		portInfo = DecodePortStr (portStr)
		if portInfo == None:
			parser.error ('Invalid port: ' + portStr)
		portInfo.index = portCount
		outputPorts.append (portInfo)
		if verbosity >= 2:
			print 'Added output port: ' + str (portInfo)
		portCount += 1

	# Parse port/pin mapping string
	mapPattern = re.compile ('(?P<inPort>\d+)(:(?P<inPin>\d+))?>((?P<mult>[-\d.]+)>)?(?P<outPort>\d+)(:(?P<outPin>\d+))?')
	for m in mapPattern.finditer (options.mapping):
		mappingString = m.string[m.start ():m.end ()]
		groups = m.groupdict ()
		try:
			if groups['inPort'] == None:
				inPort = 0
			else:
				inPort = int (groups['inPort'])
			if groups['inPin'] == None:
				inPin = 0
			else:
				inPin = int (groups['inPin'])
			if groups['mult'] == None:
				mult = None
			else:
				mult = float (groups['mult'])
			if groups['outPort'] == None:
				outPort = 0
			else:
				outPort = int (groups['outPort'])
			if groups['outPin'] == None:
				outPin = 0
			else:
				outPin = int (groups['outPin'])
		except ValueError, e:
			parser.error ('Bad value in mapping "' + mappingString + '": ' + str (e))
		#if options.verbosity >= 2:
			#print 'Processing mapping "' + mappingString + \
				#'" input = %d:%d\tmultiplier = %s\toutput = %d:%d' % (inPort, inPin, str (mult), outPort, outPin)

		if inPort < 0 or inPort >= len (inputPorts):
			parser.error ('Bad input port number in mapping "' + mappingString + '"')
		if (inPin < 0 or inPin >= inputPorts[inPort].length) and inputPorts[inPort].length != 0:
			parser.error ('Bad input pin number in mapping "' + mappingString + '"')
		if outPort < 0 or outPort >= len (outputPorts):
			parser.error ('Bad output port number in mapping "' + mappingString + '"')
		if (outPin < 0 or outPin >= outputPorts[outPort].length) and outputPorts[outPort].length != 0:
			parser.error ('Bad output pin number in mapping "' + mappingString + '"')

		# Get conversion function for this output pin
		if inputPorts[inPort].type == outputPorts[outPort].type:
			# Same type, no conversion necessary
			convFunc = None
			postMultiply = False
		else:
			convFunc, postMultiply = GetConversionFunction (inputPorts[inPort].type.__name__, outputPorts[outPort].type.__name__)
			if convFunc == None:
				return False

		# Set the entry in the map
		if outputPorts[outPort].length == 0:
			outputPorts[outPort].sourceMap = PinMapping (inPort, inPin, mult, postMultiply, convFunc)
		else:
			outputPorts[outPort].sourceMap[outPin] = PinMapping (inPort, inPin, mult, postMultiply, convFunc)

	if options.verbosity:
		verbosity = options.verbosity
		print 'Output map:'
		PrintMap (outputPorts)

	# Strip the options we use from sys.argv to avoid confusing the manager's option parser
	sys.argv = [option for option in sys.argv if option not in parser._short_opt.keys () + parser._long_opt.keys ()]
	return True


def main ():
	# Check options for ports
	if not GetPortOptions ():
		return 1

	mgr = OpenRTM_aist.Manager.init (len (sys.argv), sys.argv)

	mgr.setModuleInitProc (FlexiFilterInit)
	mgr.activateManager ()
	mgr.runManager ()

if __name__ == "__main__":
	main ()
