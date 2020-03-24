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

files = {
	"all" : "tempResult/cpu/all.json",
	"edged" : "tempResult/cpu/edged.json",
	"dbus-daemon" : "tempResult/cpu/dbus-daemon.json",
	"handoff" : "tempResult/handoff.json",
	"flowcount" : "tempResult/flowcount.txt",
	"counters" : "tempResult/counters.json",
	"perf stat" : "tempResult/perf/stat",
	# "perfReport_cpu" : "tempResult/perf/report/cpu/",
	# "perfReport_drops" : "tempResult/perf/report/drops/"
}

commandList = {
	"handoff" : "debug.py -v --handoff ",
	"flowcount" : "dispcnt -s mod_fc -z ",
	"counters" : "getcntr -c",
	"perf stat" : "perf stat"
}

class CustomTimer(_Timer):
	def __init__(self, interval, function, args=[], kwargs={}):
		self._original_function = function
		super(CustomTimer, self).__init__(interval, self._do_execute, args, kwargs)

	def _do_execute(self, *a, **kw):
		self.result = self._original_function(*a, **kw)

	def join(self):
		super(CustomTimer, self).join()
		return self.result

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
			directories = directory.split('/')					# TODO : what if from root
			directoryPath = ''
			for directory in directories :
				directoryPath += directory 
				createDirectory(directoryPath)
				directoryPath += '/'

def clearDirectory(directory):
	if os.path.exists(directory) :
		shutil.rmtree(directory)

def moveDirectory(sourceDirectory, destinationDirectory):
	if not os.path.exists(destinationDirectory) :
		createDirectory(destinationDirectory)	
	shutil.move(sourceDirectory, destinationDirectory)

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
	fileAddr = files[key]
	return fileAddr

def findIndex(data, proc) :
	for index in range(len(data['all'])) :
		if proc.pid == data['all'][index]['pid'] :
			return index
	return -1

def executeCommand(command) :
	result = commands.getoutput(command)
	return result

def generateFileName(directory, pid, timeStamp) :
	fileName = directory + '/' + str(pid) + '_' + str(timeStamp) + '.txt'
	return fileName

def getNoOfSample(sampleFrequency, duration):
	noOfSample = (duration / sampleFrequency) + 1
	return noOfSample

def getCpuPercent(proc, t):
   total_percent = proc.cpu_percent(interval = 0.1)
   total_time = sum(proc.cpu_times())
   return total_percent * ((t.system_time + t.user_time)/total_time)

def getThread(proc, thread) :

	threadEntry = {}
	threadEntry['tid'] = thread.id

	try:
		t = psutil.Process(thread.id)
		threadEntry['name'] = t.name()
	except:
		threadEntry['name'] = proc.name()
		proc.cpu_percent(interval = 0.1)

	try:
		threadEntry['cpu_percent'] = getCpuPercent(proc, thread)
	except:
		threadEntry['cpu_percent'] = 0.0						# TODO : handle 

	threadEntry['user_time'] = thread.user_time
	threadEntry['system_time'] = thread.system_time

	return threadEntry
	

def getProcessSamples(proc) :
	sample = {}
	timeStamp = time.time()
	sample[timeStamp] = {}
	sample[timeStamp]['cpu_percent'] = proc.cpu_percent(interval = 0.1)
	sample[timeStamp]['threads'] = []

	threadObjects = []
	for thread in proc.threads() :
		# sample[timeStamp]['threads'].append(getThread(proc, thread))
		t = CustomTimer(0, getThread, [proc, thread])
		t.start()
		threadObjects.append(t)
		
	for t in threadObjects:
		sample[timeStamp]['threads'].append(t.join())

	return sample

def getProcessDetails(proc) :
	processEntry = OrderedDict()
	processEntry['pid'] = proc.pid
	processEntry['name'] = proc.name()
	processEntry['samples'] = []

	return processEntry

def collectNextProcessSample(input, lock) :
	for process in input["cpu"]:

		fileAddr = getFileAddr(process)

		with lock:
			data = loadData(fileAddr)

			if process == 'all' :
				for proc in psutil.process_iter():
					index = findIndex(data, proc)
					if(index == -1):
						data[process].append(getProcessDetails(proc))
						index = len(data['all']) - 1
					data[process][index]['samples'].append(getProcessSamples(proc))
			else :
				try:
					pid = data[process]["pid"]
					data[process]['samples'].append(getProcessSamples(psutil.Process(pid)))
				except:
					pass
			writeFile(data, fileAddr)

def getCpuProfile(input, noOfSample, sampleFrequency):					# just making a room for process

	lock = threading.Lock()

	for process in input["cpu"]:
		output = {}
		if process == 'all' :
			output[process] = []
			for proc in psutil.process_iter():
				output[process].append(getProcessDetails(proc))
		else :
			output[process] = {}
			for proc in psutil.process_iter():
				if proc.name() == process:
					output[process] = getProcessDetails(proc)
					break

		fileAddr = getFileAddr(process)
		writeFile(output, fileAddr)

	threadObjects = []
	delay = 0
	while noOfSample > 0 :
		tObj = threading.Timer(delay, collectNextProcessSample, [input, lock])
		tObj.start()
		threadObjects.append(tObj)
		delay += sampleFrequency
		noOfSample -= 1

	for tObj in threadObjects:
		tObj.join()

def getHandoff(fileAddr, noOfSample, sampleFrequency) :
	output = {}
	output['handoff'] = []

	delay = 0
	while noOfSample > 0 :

		noOfSample -= 1
		sample = {}
		c = CustomTimer(delay, executeCommand, [commandList['handoff']])		#actual
		c.start()
		entry = {}
		entry = c.join()
		sample[time.time()] = eval(entry)
		output['handoff'].append(sample)
		delay = sampleFrequency

	writeFile(output, fileAddr)

def getCounterSamples(input):
	count = {}
	for cntr in input["counters"]:
		c = CustomTimer(0, executeCommand, ["{0} {1}".format(commandList['counters'], cntr)])		# actual
		c.start()
		count[cntr] = c.join()
	return count

def getCounters(input, noOfSample, sampleFrequency) :
	output = {}
	output["counters"] = []

	delay = 0
	while noOfSample > 0 :
		noOfSample -= 1
		sample = {}
		
		c = CustomTimer(delay, getCounterSamples, [input])
		c.start()

		sample[time.time()] = c.join()
		output['counters'].append(sample)
		delay = sampleFrequency

	fileAddr = getFileAddr("counters")
	writeFile(output, fileAddr)

def getPerfStatSamples(input, directory):
	timeStamp = time.time()
	for process in psutil.process_iter():			# TODO : should be from all.json
		fileAddr = generateFileName(directory, process.pid, timeStamp)

		c = CustomTimer(0, executeCommand, ["{0} -e {1} sleep 0.01".format(commandList['perf stat'], ','.join(input["perf stat"]))])
		c.start()
		writeTxtFile(c.join(), fileAddr)

def getPerfStat(input, noOfSample, sampleFrequency) :
	delay = 0
	directory = getFileAddr("perf stat")
	while noOfSample > 0 :
		noOfSample -= 1
		threading.Timer(delay, getPerfStatSamples, [input, directory]).start()
		delay += sampleFrequency

targetFunction = {
	"cpu" : getCpuProfile,
	"handoff" : getHandoff,
	"counters" : getCounters,
	"perf stat" : getPerfStat
}

def getDiagDump(input, noOfSample):

	for key in input.keys():

		threadObjects = []

		if key == "cpu":
			createDirectory('tempResult/{0}'.format(key))
			t1 = threading.Thread(target = targetFunction[key], args = (input, noOfSample, input['sampleFrequency'], ))
			t1.start()
			# threadObjects.append(t)

		elif key == "commands":
			for cmd in input[key]:
				t2 = threading.Thread(target = targetFunction[cmd], args = (getFileAddr(cmd), noOfSample, input['sampleFrequency'], ))
				t2.start()
				# threadObjects.append(t)

		elif key == "counters" :
			t3 = threading.Thread(target = targetFunction[key], args = (input, noOfSample, input['sampleFrequency'], ))
			t3.start()
			# threadObjects.append(t)

		elif key == "perf stat" :
			createDirectory("tempResult/perf/stat")
			t4 = threading.Thread(target = targetFunction[key], args = (input, noOfSample, input['sampleFrequency'], ))
			t4.start()
			# threadObjects.append(t)

	# for threadObj in threadObjects :				# Not working this way
	# 	threadObj.join()
	# 	print("done")
	t1.join()
	t2.join()
	t3.join()
	t4.join()

def doPerfRecord(outputDirectory) :
	global isRecording
	isRecording = 1
	print("recording")
	res = executeCommand("perf record -s -F 999 -a --call-graph dwarf -- sleep 3 > {0}/tempResult/perf.data".format(outputDirectory))
	print("recorded")

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
	return handoff

def findCriticalThreads_cpuBased(threshold, outputDirectory) :

	data = loadData(outputDirectory + '/' + getFileAddr("all"))
	threadWithCpuPercent = defaultdict(dict)

	global isRecording

	for process in data["all"] :
		for ts in process["samples"] :
			for thread in ts[ts.items()[0][0]]["threads"] :
				try:																		# TODO : try block required?
					if thread['cpu_percent'] >= threshold:

						if not isRecording:
							doPerfRecord(outputDirectory)

						threadWithCpuPercent[thread['tid']]['name'] = thread['name']
						if not threadWithCpuPercent[thread["tid"]].has_key('cpuPercent') :
							threadWithCpuPercent[thread["tid"]]['cpuPercent'] = []
						threadWithCpuPercent[thread["tid"]]['cpuPercent'].append(thread["cpu_percent"])
				except:
					pass

	sortedRes = OrderedDict()

	for key, value in sorted(threadWithCpuPercent.items(), key = lambda item : sum(item[1]['cpuPercent']) / len(item[1]['cpuPercent']), reverse = True):
		sortedRes[key] = value

	return sortedRes

def findCriticalThreads_dropBased(threshold, outputDirectory) :

	handoff = loadData(outputDirectory + '/' + files["handoff"]) 
	handoff = poisonQueue(handoff)

	global isRecording

	threadWithDrop = defaultdict(dict)

	for ts in handoff["handoff"]:
		TS = ts.items()[0][0]
		for queue in ts[TS]['handoffq']:
			if queue['drops'] >= threshold :

				if not isRecording:
					doPerfRecord(outputDirectory)

				threadWithDrop[queue['tid']]['name'] = queue['name']		# TODO : has_key()
				if not threadWithDrop[queue['tid']].has_key('drops') :
					threadWithDrop[queue['tid']]['drops'] = []				
				threadWithDrop[queue['tid']]['drops'].append(queue['drops'])

	sortedRes = OrderedDict()
	
	for key, value in sorted(threadWithDrop.items(), key = lambda item : item[1]['drops'][len(threadWithDrop[item[0]]['drops']) - 1] - item[1]['drops'][0], reverse = True):
		sortedRes[key] = value

	return sortedRes

def getTop10(sortedRes):
	top10 = OrderedDict()
	count = 0
	for key in sortedRes.keys():
		if count < 10 :
			top10[key] = sortedRes[key]
			count +=1
		else :
			break
	return top10

def findCriticalThreads(key, threshold, outputDirectory) :

	sortedRes = OrderedDict()

	if key == "cpu" :
		sortedRes = findCriticalThreads_cpuBased(threshold, outputDirectory)
	elif key == "drops" :
		sortedRes = findCriticalThreads_dropBased(threshold, outputDirectory)

	return getTop10(sortedRes)


def isFileExists(fileName, directory):
	if commands.getoutput('find {0} -name {1}'.format(directory, fileName)):
		return 1
	time.sleep(1)
	return 0

def doPerfReport(key, criticalThreads, outputDirectory, timeStamp):
	print("reporting....")
	global isRecording 

	if isRecording:
		while not isFileExists('perf.data', outputDirectory + '/tempResult'):
			pass

	directory = '{0}/perfReport'.format(outputDirectory)
	createDirectory(directory)

	for tid in criticalThreads:
		fileName = generateFileName(directory, key + '_' + str(tid), timeStamp)
		# res = executeCommand("perf report --tid={0} --stdio > {1}".format(tid, fileName))
		res = executeCommand("perf report --call-graph=none --tid={0} > {1}".format(tid, fileName))

def printTable(outputDirectory, key, criticalThreads, timeStamp):
	print("printing....")
	if key == 'cpu' :
		displayName = 'Thread Name'
	elif key == 'drops':
		displayName = 'Handoff Queue Name'

	table = PrettyTable([displayName, key, "perf report"])
	table.align['perf report'] = 'l'

	for tid in criticalThreads:
		report = ''
		with open('{0}/perfReport/{1}_{2}_{3}.txt'.format(outputDirectory, key, tid, timeStamp), 'r') as fObj:
			content = fObj.readlines()[8:-4]
			report = report.join(content)

		if key == "cpu":
			table.add_row([criticalThreads[tid]['name'], sum(criticalThreads[tid]['cpuPercent']) / len(criticalThreads[tid]['cpuPercent']) , report])
		elif key =="drops":
			increaseRate = criticalThreads[tid]['drops'][len(criticalThreads[tid]['drops']) - 1] - criticalThreads[tid]['drops'][0]
			totalDrops = criticalThreads[tid]['drops'][len(criticalThreads[tid]['drops']) - 1]
			table.add_row([criticalThreads[tid]['name'], str(increaseRate) + '(' + str(totalDrops) + ')', report])
	print(table)
	del table

def checkForThresholdHits(trigger, outputDirectory, timeStamp):

	for key in trigger:
		threshold = trigger[key]
		top10 = findCriticalThreads(key, threshold, outputDirectory)															
		if top10:
			doPerfReport(key, top10, outputDirectory, timeStamp)
			printTable(outputDirectory, key, top10, timeStamp)

	global isRecording
	isRecording = 0
	os.remove('perf.data')

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

def createManifest(outputDirectory):
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

	with open("{0}/tempResult/MANIFEST.json".format(outputDirectory), "w") as wObj:
		json.dump(manifest, wObj, indent = 4, sort_keys = False)

def checkAndDelete(outputDirectory):
	availableZip = commands.getoutput("find {0} -name '*.zip'".format(outputDirectory))
	availableZip = (availableZip.split('\n'))
	availableZip.sort()
	if len(availableZip) == 2:
		sts = commands.getoutput('rm {0}'.format(availableZip[0]))

def zipOutput(outputDirectory, timeStamp):

	moveDirectory('{0}/tempResult'.format(outputDirectory), '{0}/diagDump_{1}'.format(outputDirectory, timeStamp))
	path = '{0}/diagDump_{1}'.format(outputDirectory, timeStamp)
	
	checkAndDelete(outputDirectory)

	with ZipFile('/{0}/diagDump_{1}.zip'.format(outputDirectory, timeStamp),'w') as zip:
		for root, directories, files in os.walk(path):
			for filename in files:
				filepath = os.path.join(root, filename)
				zip.write(filepath)
	clearDirectory('{0}/diagDump_{1}'.format(outputDirectory, timeStamp))

def unZipOutput(filename, outputDirectory):

	with ZipFile(filename, "r") as zip:
		zip.extractall()

		filePath = str(filename).split("'")[1]
		cwd = os.getcwd()

		dirList = filePath.split('/')

		if dirList[0] != '':					# relative path
			filePath = cwd + '/' + filePath
			dirList = filePath.split('/')

		dir = dirList[len(dirList) - 1].split('.zip')[0]
		dirList[len(dirList) - 1] = dir
		opPath = '/'.join(dirList)

		sts = shutil.move('{0}{1}/tempResult'.format(cwd, opPath), '{0}/tempResult'.format(outputDirectory))
		sts = shutil.rmtree('root')

isRecording = 0									# global

def main():
	input = loadData("input.json")
	clearDirectory('tempResult')
	createDirectory(input['outputDirectory'])

	argDict = parseCommandLineArguments()

	if argDict.items()[0][1] != None:			# cmdline arg is there
		timeStamp = time.time()
		unZipOutput(argDict.items()[0][1], input['outputDirectory'])
		checkForThresholdHits(input['triggers'], input['outputDirectory'], timeStamp)
		clearDirectory(input['outputDirectory'] + '/tempResult')
		pass

	else:
		consecutiveThresholdExceedLimit = input['consecutiveThresholdExceedLimit']
		while True:

			if consecutiveThresholdExceedLimit > 0:

				print("started")
				print(consecutiveThresholdExceedLimit)
				timeStamp = time.time()

				createDirectory('tempResult')

				noOfSample = getNoOfSample(input['sampleFrequency'], input['duration'])

				getDiagDump(input, noOfSample)
				print("diagdump collected")

				moveDirectory('tempResult', input['outputDirectory'])
			
				checkForThresholdHits(input['triggers'], input['outputDirectory'], timeStamp)
				createManifest(input['outputDirectory'])
				zipOutput(input['outputDirectory'], timeStamp)

				consecutiveThresholdExceedLimit -= 1

			if consecutiveThresholdExceedLimit == 0 or input['auto mode'] == 0:
				print("break...")
				break
		

if __name__ == "__main__" :
	main()
