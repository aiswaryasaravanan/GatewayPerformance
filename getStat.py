from __future__ import with_statement
import psutil
import json
import argparse
import os
import shutil
import commands
import random
import time
import threading
from threading import _Timer
from collections import OrderedDict, defaultdict
from prettytable import PrettyTable
from zipfile import ZipFile
import subprocess

files = {
	"all" : "tempResult/cpu/all.json",
	"edged" : "tempResult/cpu/edged.json",
	"dbus-daemon" : "tempResult/cpu/dbus-daemon.json",
	"handoff" : "tempResult/commands/handoff.json",
	"flowcount" : "tempResult/flowcount.txt",
	"counters" : "tempResult/counters.json",
	"perf stat" : "tempResult/perf/stat",
	"perf report" : "tempResult/perf/report",
}

commandList = {
	"handoff" : "debug.py -v --handoff ",
	# "flowcount" : "dispcnt -s mod_fc -z ",
	"counters" : "getcntr -c",
	"perf stat" : "perf stat"
}


def parseCommandLineArguments():
	parser = argparse.ArgumentParser()
	parser.add_argument("-F", "--filename", help="output zip file", type = file)
	args = parser.parse_args()
	return vars(args)

def createDirectory(directory) :
	try :
		os.mkdir(directory)
	except :
		if os.path.exists(directory):							# File exists
			pass
		else :													# No such file or directory 
			directories = directory.split('/')					
			directoryPath = ''
			for d in directories :
				if d == '':
					directoryPath += '/'
					pass
				directoryPath += d
				createDirectory(directoryPath)
				directoryPath += '/'

def clearDirectory(directory):
	if os.path.exists(directory) :
		shutil.rmtree(directory)

def moveDirectory(sourceDirectory, destinationDirectory):
	if not os.path.exists(destinationDirectory) :
		createDirectory(destinationDirectory)	
	shutil.move(sourceDirectory, destinationDirectory)

class CustomTimer(_Timer):
	def __init__(self, interval, function, args=[], kwargs={}):
		self._original_function = function
		super(CustomTimer, self).__init__(interval, self._do_execute, args, kwargs)

	def _do_execute(self, *a, **kw):
		self.result = self._original_function(*a, **kw)

	def join(self):
		super(CustomTimer, self).join()
		return self.result

def loadData(fileAddr):
	with open(fileAddr) as rObj:
		data = json.load(rObj)
	return data

def writeFile(output, fileAddr):
	with open(fileAddr, "w") as wObj:		
		json.dump(output, wObj, indent = 4, sort_keys = False)

def writeTxtFile(output, fileAddr) :
	with open(fileAddr, "w") as wObj:		
		wObj.write(output)

def getFileAddr(key):
	if not files.has_key(key):
		files.setdefault(key, 'tempResult/commands/{0}.txt'.format(key.split(' ')[0]))
	return files[key]

def getCommandList(key):
	if commandList.has_key(key):
		return commandList[key]
	return key 						# for custom commands

def findIndex(data, proc) :
	for index in range(len(data['all'])) :
		if proc.pid == data['all'][index]['pid'] :
			return index
	return -1

def executeCommand(command) :
	result = commands.getoutput(command)
	return result

def generateFileName(directory, pid) :
	fileName = directory + '/' + str(pid) + '.txt'
	return fileName

def getNoOfSample(sampleFrequency, duration):
	noOfSample = (duration / sampleFrequency) + 1
	return noOfSample

def doTriggerFlow():
	doPerfRecord()

def getCpuPercent(proc, t):
   total_percent = proc.cpu_percent(interval = 0.1)
   total_time = sum(proc.cpu_times())
   return total_percent * ((t.system_time + t.user_time)/total_time)

def getThread(proc, thread, process) :

	global isTriggered

	threadEntry = {}
	threadEntry['tid'] = thread.id

	t = psutil.Process(thread.id)
	threadEntry['name'] = t.name()
	try:
		threadEntry['cpu_percent'] = getCpuPercent(proc, thread)
	except:
		threadEntry['cpu_percent'] = 0.0	
	threadEntry['user_time'] = thread.user_time
	threadEntry['system_time'] = thread.system_time	

	if autoMode and isTriggered == 0:
		if process.has_key('trigger'):
			if threadEntry['cpu_percent'] >= process['trigger']:
				print('triggered -> cpu')
				key = 'cpu'
				doTriggerFlow()
				isTriggered = 1
			
	return threadEntry
	

def getProcessSamples(proc, process) :
	sample = {}
	timeStamp = time.time()
	sample[timeStamp] = {}
	sample[timeStamp]['cpu_percent'] = proc.cpu_percent(interval = 0.1)
	# sample[timeStamp]['threads'] = []

	threadObjects = []
	for thread in proc.threads() :
		if not sample[timeStamp].has_key('thread'):
			sample[timeStamp]['threads'] = []
		t = CustomTimer(0, getThread, [proc, thread, process])
		t.start()
		threadObjects.append(t)
		
	for t in threadObjects:
		sample[timeStamp]['threads'].append(t.join())

	return sample

def getProcessDetails(proc) :
	processEntry = OrderedDict()

	try:
		processEntry['pid'] = proc.pid
		processEntry['name'] = proc.name()
		processEntry['samples'] = []
	except:
		pass
	return processEntry

def collectNextProcessSample(cpu, lock) :
	for process in cpu:
		processName = process['name']
		fileAddr = getFileAddr(processName)

		with lock:
			data = loadData(fileAddr)

			if processName == 'all' :
				for proc in psutil.process_iter():
					index = findIndex(data, proc)
					if(index == -1):
						data[processName].append(getProcessDetails(proc))
						index = len(data['all']) - 1
					data[processName][index]['samples'].append(getProcessSamples(proc, process))
			else :
				try:
					pid = data[processName]["pid"]
					data[processName]['samples'].append(getProcessSamples(psutil.Process(pid), process))
				except:
					pass
			writeFile(data, fileAddr)

def getCpuProfile(cpu, noOfSample, sampleFrequency):					# making a room for process

	lock = threading.Lock()

	for process in cpu:
		processName = process['name']
		output = {}
		if processName == 'all' :
			output[processName] = []
			for proc in psutil.process_iter():
				output[processName].append(getProcessDetails(proc))
		else :
			output[processName] = {}
			for proc in psutil.process_iter():
				if proc.name() == processName:
					output[processName] = getProcessDetails(proc)
					break

		fileAddr = getFileAddr(processName)
		writeFile(output, fileAddr)

	threadObjects = []
	delay = 0
	while noOfSample > 0 :
		tObj = threading.Timer(delay, collectNextProcessSample, [cpu, lock])
		tObj.start()
		threadObjects.append(tObj)
		delay += sampleFrequency
		noOfSample -= 1

	for tObj in threadObjects:
		tObj.join()

def getHandoff(fileAddr, command, noOfSample, sampleFrequency) :
	output = {}
	output['handoff'] = []
	global isTriggered

	delay = 0
	while noOfSample > 0 :

		noOfSample -= 1
		sample = {}
		c = CustomTimer(delay, executeCommand, [getCommandList(command['name'])])		
		c.start()
		timeStamp = time.time()
		entry = {}
		entry = c.join()
		sample[timeStamp] = eval(entry)
		output['handoff'].append(sample)
		delay = sampleFrequency

		if autoMode and isTriggered == 0:
				outputPoisoned = poisonQueue(output)

				index = len(outputPoisoned['handoff']) - 1
				TS = outputPoisoned['handoff'][index]
				for queue in TS[TS.items()[0][0]]['handoffq']:
					if queue['drops'] >= command['trigger']:
						print('triggered - > handoff')
						key = 'drops'
						doTriggerFlow()
						isTriggered = 1

	writeFile(output, fileAddr)

def getCustomCommands(fileName, command, noOfSample, sampleFrequency):
	commandOutput = executeCommand('{0} > {1}'.format(getCommandList(command['name']), fileName))
	
def getDpdkInterfaceNames():
	dpdkPortsDump = commands.getoutput('debug.py -v --dpdk_ports_dump')
	dpdkPortsDump = eval(dpdkPortsDump)
	dpdkInterfaceNames = []
	for dump in dpdkPortsDump:
		dpdkInterfaceNames.append(dump['name'])
	return dpdkInterfaceNames

def getCounterSamples(counters):
	
	dpdkInterfaceNames = getDpdkInterfaceNames()
	countersList = {}
	for name in dpdkInterfaceNames:
		countersList['dpdk_{0}_pstat_ierrors'.format(name)] = executeCommand('{0} dpdk_{1}_pstat_ierrors'.format(commandList['counters'], name))
		countersList['dpdk_{0}_pstat_oerrors'.format(name)] = executeCommand('{0} dpdk_{1}_pstat_oerrors'.format(commandList['counters'], name))
		countersList['dpdk_{0}_pstat_imissed'.format(name)] = executeCommand('{0} dpdk_{1}_pstat_imissed'.format(commandList['counters'], name))

	for cntr in counters:
		c = CustomTimer(0, executeCommand, ["{0} {1}".format(commandList['counters'], cntr['name'])])		# actual
		c.start()
		countersList[cntr['name']] = c.join()

	return countersList

def getCounters(counters, noOfSample, sampleFrequency) :
	output = {}
	output["counters"] = []

	delay = 0
	while noOfSample > 0 :
		noOfSample -= 1
		sample = {}
		
		c = CustomTimer(delay, getCounterSamples, [counters])
		c.start()

		sample[time.time()] = c.join()
		output['counters'].append(sample)
		delay = sampleFrequency						# for now

	fileAddr = getFileAddr("counters")
	writeFile(output, fileAddr)

targetFunction = {
	"cpu" : getCpuProfile,
	"handoff" : getHandoff,
	"counters" : getCounters,
}

def getTargetFunction(key):
	if not targetFunction.has_key(key):
		targetFunction.setdefault(key, getCustomCommands)
	return targetFunction[key]


def getDiagDump(input, noOfSample):

	for key in input.keys():

		# threadObjects = []

		if key == "cpu":
			createDirectory('tempResult/{0}'.format(key))
			t1 = threading.Thread(target = targetFunction[key], args = (input['cpu'], noOfSample, input['sampleFrequency'], ))
			t1.start()
			# threadObjects.append(t)

		elif key == "commands":
			createDirectory('tempResult/{0}'.format(key))
			for cmd in input[key]:
				commandName = cmd['name']
				t2 = threading.Thread(target = getTargetFunction(commandName), args = (getFileAddr(commandName), cmd, noOfSample, input['sampleFrequency'], ))
				t2.start()
				# threadObjects.append(t)

		elif key == "counters" :
			t3 = threading.Thread(target = targetFunction[key], args = (input['counters'], noOfSample, input['sampleFrequency'], ))
			t3.start()
			# threadObjects.append(t)

	# for threadObj in threadObjects :				# Not working this way
	# 	threadObj.join()
	# 	print("done")
	t1.join()
	t2.join()
	t3.join()

def doPerfRecord() :
	createDirectory('tempResult/perf')
	res = executeCommand("perf record -s -F 999 -a --call-graph dwarf -- sleep 3 > tempResult/perf/perf.data")
	# sts = subprocess.Popen("perf record -s -F 999 -a --call-graph dwarf -- sleep 3 > tempResult/perf/perf.data &", shell = True)
	# time.sleep(3)		# as of now
	# return sts.pid

def modifyDrop(drop) :
	drop += random.randint(1, 1000)
	return drop

def poisonQueue(handoff) :

	flag = 1
	for ts in handoff["handoff"] :
		if flag :
			pre = ts
			flag = 0
			continue

		for queue in range(len(ts[ts.items()[0][0]]["handoffq"])) :
			ts[ts.items()[0][0]]["handoffq"][queue]["drops"] = modifyDrop(pre[pre.items()[0][0]]["handoffq"][queue]["drops"])
		pre = ts

	writeFile(handoff, getFileAddr('handoff'))
	return handoff

def poisonCounters(counters) :
	flag = 1
	for TS in counters['counters']:
		if flag :
			pre = TS
			flag = 0
			continue

		for counter in TS[TS.items()[0][0]]:
			TS[TS.items()[0][0]][counter] = modifyDrop(int(pre[pre.items()[0][0]][counter]))
		pre = TS

	writeFile(counters, getFileAddr('counters'))
	return counters

def getTop10(data):

	top10 = OrderedDict()
	count = 0
	for key in data.keys():
		if count < 10 :
			top10[key] = data[key]
			count +=1
		else :
			break
	return top10

def counterBasedCriticalItems():
	counters = loadData(files['counters'])
	counters = poisonCounters(counters)

	criticalItems = defaultdict()

	for TS in counters['counters']:
		for counter in TS[TS.items()[0][0]]:
			drop = TS[TS.items()[0][0]][counter]
			if not criticalItems.has_key(counter):
				criticalItems[counter] = []
			criticalItems[counter].append(int(drop))

	sortedRes = OrderedDict()
	for key, value in sorted(criticalItems.items(), key = lambda item : item[1][len(item[1]) - 1] - item[1][0], reverse =True):
		sortedRes[key] = value

	return getTop10(sortedRes)


def dropBasedCriticalItems():
	handoff = loadData(files["handoff"]) 
	handoff = poisonQueue(handoff)

	criticalItems = defaultdict(dict)

	for ts in handoff["handoff"]:
		TS = ts.items()[0][0]
		for queue in ts[TS]['handoffq']:
				criticalItems[queue['tid']]['name'] = queue['name']		# TODO : has_key()
				if not criticalItems[queue['tid']].has_key('drops') :
					criticalItems[queue['tid']]['drops'] = []				
				criticalItems[queue['tid']]['drops'].append(queue['drops'])

	sortedRes = OrderedDict()
	
	for key, value in sorted(criticalItems.items(), key = lambda item : item[1]['drops'][len(criticalItems[item[0]]['drops']) - 1] - item[1]['drops'][0], reverse = True):
		sortedRes[key] = value

	return getTop10(sortedRes)

def cpuBasedCriticalItems():
	data = loadData(getFileAddr("all"))
	criticalItems = defaultdict(dict)

	for process in data["all"] :
		for ts in process["samples"] :
			for thread in ts[ts.items()[0][0]]["threads"] :
				criticalItems[thread['tid']]['name'] = thread['name']
				if not criticalItems[thread["tid"]].has_key('cpuPercent') :
					criticalItems[thread["tid"]]['cpuPercent'] = []
				criticalItems[thread["tid"]]['cpuPercent'].append(thread["cpu_percent"])

	sortedRes = OrderedDict()

	for key, value in sorted(criticalItems.items(), key = lambda item : sum(item[1]['cpuPercent']) / len(item[1]['cpuPercent']), reverse = True):
		sortedRes[key] = value

	return getTop10(sortedRes)

def extractCriticalItems(input):
	criticalItems = defaultdict(dict)
	criticalItems['cpu'] = cpuBasedCriticalItems()
	criticalItems['drops'] = dropBasedCriticalItems()
	criticalItems['counters'] = counterBasedCriticalItems()
	return criticalItems

def isFileExists(fileName, directory):
	if os.path.exists('tempResult/perf') and commands.getoutput('find {0} -name {1}'.format(directory, fileName)):
		return 1
	return 0

def doReport(directory, tid):
	fileName = generateFileName(directory, str(tid))
	# res = executeCommand("perf report --tid={0} --stdio > {1}".format(tid, fileName))
	res = executeCommand("perf report --call-graph=none --tid={0} > {1}".format(tid, fileName))

def doStat(events, directory, tid):
	fileName = generateFileName(directory, str(tid))
	c = CustomTimer(0, executeCommand, ["{0} -e {1} -t {2} sleep 0.01".format(commandList['perf stat'], ','.join(events), tid)])
	c.start()
	writeTxtFile(c.join(), fileName)

def collectPerfStat(events, criticalItems) :
	
	for key in criticalItems:
		if key != 'counters':
			directory = '{0}/{1}'.format(getFileAddr('perf stat'), key)
			createDirectory(directory)
			for tid in criticalItems[key]:
				doStat(events, directory, tid)

def collectPerfReport(criticalItems):					

	while not isFileExists('perf.data', 'tempResult/perf'):
		pass

	for key in criticalItems:
		if key != 'counters':
			directory = '{0}/{1}'.format(getFileAddr('perf report'), key)
			createDirectory(directory)
			for tid in criticalItems[key]:
				doReport(directory, tid)
		
def alignTable(tableObject, fields, alignment):
	for field in fields :
		tableObject.align[field] = alignment

def printTable(criticalItems):
	for key in criticalItems:
		if key == 'cpu':
			fields = ['Thread Name', key, "perf Report", "Perf Stat"]
		elif key == 'drops':
			fields = ['Handoff Queue Name', key, "perf Report", "Perf Stat"]
		elif key == 'counters':
			fields = ['Counter Name', 'drops']

		table = PrettyTable(fields)
		alignTable(table, fields, 'l')

		if key != 'counters':
			for tid in criticalItems[key]:

				report = ''
				with open(generateFileName('{0}/{1}'.format(getFileAddr('perf report'), key), tid), 'r') as fObj:
					content = fObj.readlines()[8:-4]
					report = report.join(content)

				stat = ''
				with open (generateFileName('{0}/{1}'.format(getFileAddr('perf stat'), key), tid), 'r') as statObj:
					content = statObj.readlines()[3:-2]
					stat = stat.join(content)

				if key == "cpu":
					table.add_row([criticalItems[key][tid]['name'], sum(criticalItems[key][tid]['cpuPercent']) / len(criticalItems[key][tid]['cpuPercent']) , report, stat])
				elif key =="drops":
					increaseRate = criticalItems[key][tid]['drops'][len(criticalItems[key][tid]['drops']) - 1] - criticalItems[key][tid]['drops'][0]
					totalDrops = criticalItems[key][tid]['drops'][len(criticalItems[key][tid]['drops']) - 1]
					table.add_row([criticalItems[key][tid]['name'], str(increaseRate) + '(' + str(totalDrops) + ')', report, stat])
		if key == 'counters':
			for name in criticalItems[key]:
				increaseRate = criticalItems[key][name][len(criticalItems[key][name]) - 1] - criticalItems[key][name][0]
				totalDrops = criticalItems[key][name][len(criticalItems[key][name]) - 1]
				table.add_row([name, str(increaseRate) + '(' + str(totalDrops) + ')'])

		print(table)
		del table

def getHardwareInfo(manifest):
	manifest['deviceModel'] = commands.getoutput('cat /opt/vc/lib/python/hardwareinfo.py | grep DEVICE_MODEL').split(' = ')[1]
	manifest['deviceFamily'] = commands.getoutput('cat /opt/vc/lib/python/hardwareinfo.py | grep DEVICE_FAMILY').split(' = ')[1]
	manifest['deviceId'] = commands.getoutput('cat /opt/vc/lib/python/hardwareinfo.py | grep DEVICE_ID').split(' = ')[1]

	return manifest

def getBuildInfo(manifest):
	manifest['version'] = commands.getoutput('edged -v | grep Version').split(':\t ')[1]
	manifest['build'] = commands.getoutput('edged -v | grep Hash').split(':\t ')[1]

	return manifest

def getLogicalId(manifest):
	manifest['logicalId'] = commands.getoutput('python /opt/vc/bin/getpolicy.py logicalId')
	return manifest

def createManifest():
	manifest = OrderedDict()

	manifest = getHardwareInfo(manifest)
	manifest = getBuildInfo(manifest)
	manifest = getLogicalId(manifest)

	manifest['timestamp'] = int(time.time())
	# dt = datetime.datetime.now()
	# manifest['datetime'] = dt 
	manifest['id'] = None
	manifest['type'] = None
	manifest['requestId'] = None
	manifest['deviceType'] = None
	manifest['deviceCategory'] = None
	manifest['reason'] = None

	with open("tempResult/MANIFEST.json", "w") as wObj:
		json.dump(manifest, wObj, indent = 4, sort_keys = False)

def checkAndDelete(outputDirectory):
	global windowSize

	availableZip = commands.getoutput("find {0} -maxdepth 1 -name '*.zip'".format(outputDirectory))
	availableZip = (availableZip.split('\n'))
	availableZip.sort()
	if len(availableZip) == windowSize:
		sts = commands.getoutput('rm {0}'.format(availableZip[0]))

def deleteTemporaryFiles():
	os.remove('perf.data')
	# clearDirectory('diagDump_{0}'.format(timeStamp))
	clearDirectory('tempResult')

def zipOutput(outputDirectory, timeStamp):

	# moveDirectory('{0}/tempResult'.format(outputDirectory), '{0}/diagDump_{1}'.format(outputDirectory, timeStamp))
	# path = '{0}/diagDump_{1}'.format(outputDirectory, timeStamp)
	path = 'tempResult'

	checkAndDelete(outputDirectory)

	with ZipFile('/{0}/diagDump_{1}.zip'.format(outputDirectory, timeStamp),'w') as zip:
		for root, directories, files in os.walk(path):
			for filename in files:
				filepath = os.path.join(root, filename)
				zip.write(filepath)

def unZipOutput(filename, outputDirectory):

	with ZipFile(filename, "r") as zip:
		zip.extractall()

autoMode = 0
isTriggered = 0
windowSize = 5

def main():

	global autoMode
	input = loadData("input.json")
	clearDirectory('tempResult')
	createDirectory(input['outputDirectory'])

	autoMode = input.has_key('auto mode')

	argDict = parseCommandLineArguments()

	if argDict.items()[0][1] != None:			# cmdline arg is there
		timeStamp = time.time()
		unZipOutput(argDict.items()[0][1], input['outputDirectory'])
		criticalItems = extractCriticalItems(input)
		printTable(criticalItems)
		deleteTemporaryFiles()			
		pass

	else:
		consecutiveThresholdExceedLimit = 0
		while True:

			createDirectory('tempResult')
			timeStamp = time.time()

			noOfSample = getNoOfSample(input['sampleFrequency'], input['duration'])

			getDiagDump(input, noOfSample)
			createManifest()

			criticalItems = extractCriticalItems(input)

			if not autoMode:
				doPerfRecord()

			collectPerfReport(criticalItems)
			collectPerfStat(input['perf stat'], criticalItems)

			printTable(criticalItems)

			zipOutput(input['outputDirectory'], timeStamp)
			deleteTemporaryFiles()

			if not autoMode :
				break

			consecutiveThresholdExceedLimit += 1
			if consecutiveThresholdExceedLimit == input['auto mode']['consecutiveThresholdExceedLimit'] :
				break
		

if __name__ == "__main__" :
	main()
