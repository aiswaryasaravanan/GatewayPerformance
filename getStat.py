import psutil
import json
import os
import shutil
import commands
import subprocess
import time
import threading
from threading import _Timer
from collections import OrderedDict

files = {
	"all" : "output/cpu/all.json",
	"edged" : "output/cpu/edged.json",
	"dbus-daemon" : "output/cpu/dbus-daemon.json",
	"handoff" : "output/handoff.json",
	"flowcount" : "output/flowcount.txt",
	"counters" : "output/counters.json",
	"perf stat" : "output/perf/"
}

commandList = {
	"handoff" : "debug.py -v --handoff ",
	"flowcount" : "dispcnt -s mod_fc -z ",
	"counters" : "getcntr -c",
	"perf stat" : "perf stat"
}
	
def clearDirectory(directory) :
	try :
		shutil.rmtree(directory)
	except :
		pass

def createDirectory(directory) :
	try :
		os.mkdir(directory)
	except :
		pass

def getFileAddr(process):
	fileAddr = files[process]
	return fileAddr

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

class CustomTimer(_Timer):
	def __init__(self, interval, function, args=[], kwargs={}):
		self._original_function = function
		super(CustomTimer, self).__init__(interval, self._do_execute, args, kwargs)

	def _do_execute(self, *a, **kw):
		self.result = self._original_function(*a, **kw)

	def join(self):
		super(CustomTimer, self).join()
		return self.result

def executeCommand(command) :
	result = 1 								#check
	result = commands.getoutput(command)
	return result

def getThread(thread) :

	print("collecting threads")

	threadEntry = {}
	threadEntry['tid'] = thread.id
	t = psutil.Process(thread.id)
	threadEntry['name'] = t.name()
	threadEntry['cpu_percent'] = t.cpu_percent(interval = 0.01) 
	threadEntry['user_time'] = thread.user_time
	threadEntry['system_time'] = thread.system_time

	return threadEntry

def getProcessSamples(proc) :

	print("collecting samples")

	sample = {}
	timeStamp = time.time()
	sample[timeStamp] = {}
	sample[timeStamp]['cpu_percent'] = proc.cpu_percent(interval = 0.01)
	sample[timeStamp]['threads'] = []

	for thread in proc.threads() :
		sample[timeStamp]['threads'].append(getThread(thread))

	print("done with the threads")

	return sample

def getProcessDetails(proc, noOfSample, sampleFrequency) :

	processEntry = OrderedDict()
	processEntry['pid'] = proc.pid
	processEntry['name'] = proc.name()
	processEntry['samples'] = []

	delay = 0
	while noOfSample > 0 :
		noOfSample -= 1

		print("before collecting samples")

		c = CustomTimer(delay, getProcessSamples, [proc])			#actual
		c.start()
		# capture return value of getProcessSamples and append
		processEntry['samples'].append(c.join())

		delay += sampleFrequency

		print("after collecting samples")

	return processEntry

def getCpuProfile(input, noOfSample, sampleFrequency) :

	for process in input['cpu']:
		output = {}
		output[process] = {}
		if process == 'all' :
			output[process] = []
			for proc in psutil.process_iter():
				print("in all")
				output[process].append(getProcessDetails(proc, noOfSample, sampleFrequency))
		else :
			for proc in psutil.process_iter():
				if proc.name() == process:
					print("in each")
					output[process] = getProcessDetails(proc, noOfSample, sampleFrequency)
		fileAddr = getFileAddr(process)
		writeFile(output, fileAddr)

def findCriticalThreads(handoff) :
	rateOfIncrease = {}

	nTS = len(handoff["handoff"]) - 1
	for TS in handoff["handoff"][0].keys():
		fTS = TS

	for TS in handoff["handoff"][nTS].keys():
		lTS = TS

	for queue in range(len(handoff["handoff"][0][fTS]["handoffq"])):
		rateOfIncrease[handoff["handoff"][0][fTS]["handoffq"][queue]["tid"]] = handoff["handoff"][nTS][lTS]["handoffq"][queue]["drops"] - handoff["handoff"][0][fTS]["handoffq"][queue]["drops"]
	
	sortedRes  = OrderedDict()
	for key, value in sorted(rateOfIncrease.items(), key = lambda item : item[1], reverse = True):
		sortedRes[key] = value

	top5 = OrderedDict()
	count = 0
	for key in sortedRes.keys():
		if count < 5 :
			top5[key] = sortedRes[key]
			count +=1
		else :
			break

	return top5

def getHandoff(fileAddr, noOfSample, sampleFrequency) :
	output = {}
	output['handoff'] = []

	delay = 0
	while noOfSample > 0 :

		noOfSample -= 1
		sample = {}
		c = CustomTimer(delay, executeCommand, [commandList['handoff']])		#actual
		c.start()
		sample[time.time()] = c.join()

		output['handoff'].append(sample)
		delay += sampleFrequency

	writeFile(output, fileAddr)

	handoff = loadData(files["handoff"]) 
	criticalThreads = findCriticalThreads(handoff)

	print(criticalThreads)


def getFlowCount(fileAddr, noOfSample, sampleFrequency) :
	c = CustomTimer(0, executeCommand, ["{0} -t {1} -r {2}".format(commandList['flowcount'], sampleFrequency, noOfSample)])	
	c.start()	
	writeTxtFile(c.join(), fileAddr)

def getCounters(input, noOfSample, sampleFrequency) :
	output = {}
	output["counters"] = []

	delay = 0
	while noOfSample > 0 :
		noOfSample -= 1
		sample = {}
		count = {}
		for cntr in input["counters"]:
			c = CustomTimer(delay, executeCommand, ["{0} {1}".format(commandList['counters'], cntr)])		# actual
			c.start()
			# capture return value of executeCommand and append
			count[cntr] = c.join()

		sample[time.time()] = count
		output['counters'].append(sample)
		delay += sampleFrequency

	fileAddr = getFileAddr("counters")
	writeFile(output, fileAddr)

def generateFileName(directory, pid, timeStamp) :
	fileName = directory + str(pid) + '_' + str(int(timeStamp)) + '.txt'
	return fileName

def getPerfStat(input, directory, noOfSample, sampleFrequency) :

	delay = 0
	while noOfSample > 0 :
		timeStamp = time.time()
		noOfSample -= 1
		for process in psutil.process_iter():
			fileAddr = generateFileName(directory, process.pid, timeStamp)
			c = CustomTimer(delay, executeCommand, ["{0} -e {1} sleep 0.01".format(commandList['perf stat'], ','.join(input["perf stat"]))])
			c.start()
			writeTxtFile(c.join(), fileAddr)	

		delay += sampleFrequency

targetFunction = {
	"cpu" : getCpuProfile,
	"handoff" : getHandoff,
	"flowcount" : getFlowCount,
	"counters" : getCounters,
	"perf stat" : getPerfStat
}

def collectStat(input, noOfSample):

	for key in input.keys():

		if key == "cpu":
			createDirectory(input['outputDirectory'] + '/' + key)
			threading.Timer(0, targetFunction[key], [input, noOfSample, input['sampleFrequency'], ]).start()

		elif key == "commands":
			for cmd in input[key]:
				threading.Thread(target = targetFunction[cmd], args = (getFileAddr(cmd), noOfSample, input['sampleFrequency'], )).start()

		elif key == "counters" :
			threading.Timer(0, targetFunction[key], [input, noOfSample, input['sampleFrequency'], ]).start()

		if key == "perf stat" :
			createDirectory("output/perf")
			threading.Timer(0, targetFunction[key], args = (input, getFileAddr(key), noOfSample, input['sampleFrequency'], )).start()

def main():

	input = loadData("input.json")
	# reset 
	clearDirectory(input['outputDirectory'])
	createDirectory(input['outputDirectory'])

	noOfSample = input["duration"] / input["sampleFrequency"]
 	collectStat(input, noOfSample)

 # 	handoff = loadData(files["handoff"]) 
	# criticalThreads = findCriticalThreads(handoff)

	# print(criticalThreads)

 	zipOutput()

if __name__ == "__main__":
	main()
