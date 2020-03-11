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
import ast
import sys
import random
from zipfile import ZipFile

files = {
	"all" : "output/cpu/all.json",
	"edged" : "output/cpu/edged.json",
	"dbus-daemon" : "output/cpu/dbus-daemon.json",
	"handoff" : "output/handoff.json",
	"flowcount" : "output/flowcount.txt",
	"counters" : "output/counters.json",
	"perf stat" : "output/perf/stat/",
	"perf report" : "output/perf/report/"
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
	result = commands.getoutput(command)
	return result

def getThread(thread) :
	try:
		threadEntry = {}
		threadEntry['tid'] = thread.id
		t = psutil.Process(thread.id)
		threadEntry['name'] = t.name()
		threadEntry['cpu_percent'] = t.cpu_percent(interval = 0.01) 
		threadEntry['user_time'] = thread.user_time
		threadEntry['system_time'] = thread.system_time

		return threadEntry
	except :
		pass

def getProcessSamples(proc) :
	sample = {}
	timeStamp = time.time()
	sample[timeStamp] = {}
	sample[timeStamp]['cpu_percent'] = proc.cpu_percent(interval = 0.1)
	sample[timeStamp]['threads'] = []

	for thread in proc.threads() :
		sample[timeStamp]['threads'].append(getThread(thread))

	return sample

def findIndex(data, proc) :
	for index in range(len(data['all'])) :
		if proc.pid == data['all'][index]['pid'] :
			return index

def collectNextProcessSample(input) :
	for process in input["cpu"]:
		fileAddr = getFileAddr(process)
		data = loadData(fileAddr)

		if process == 'all' :
			for proc in psutil.process_iter():
				index = findIndex(data, proc)
				data[process][index]['samples'].append(getProcessSamples(proc))
		else :
			for proc in psutil.process_iter():
				if proc.name() == process:
					data[process]['samples'].append(getProcessSamples(proc))
		writeFile(data, fileAddr)

def getProcessDetails(proc) :

	processEntry = OrderedDict()
	processEntry['pid'] = proc.pid
	processEntry['name'] = proc.name()
	processEntry['samples'] = []

	return processEntry

def getCpuProfile(input, noOfSample, sampleFrequency):
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

	t = []

	delay = 0
	while noOfSample > 0 :
		noOfSample -= 1
		tObj = threading.Timer(delay, collectNextProcessSample, [input])
		tObj.start()
		t.append(tObj)
		delay += sampleFrequency

	for tObj in t:
		tObj.join()

def findCriticalThreads() :

	handoff = loadData(files["handoff"]) 
	handoff = poisonQueue(handoff)

	rateOfIncrease = {}

	nTS = len(handoff["handoff"]) - 1
	fTS = handoff["handoff"][0].items()[0][0]
	lTS = handoff["handoff"][nTS].items()[0][0]

	for queue in range(len(handoff["handoff"][0][fTS]["handoffq"])):
		rateOfIncrease[handoff["handoff"][0][fTS]["handoffq"][queue]["tid"]] = handoff["handoff"][nTS][lTS]["handoffq"][queue]["drops"] - handoff["handoff"][0][fTS]["handoffq"][queue]["drops"]
	
	# sort
	sortedRes  = OrderedDict()
	for key, value in sorted(rateOfIncrease.items(), key = lambda item : item[1], reverse = True):
		sortedRes[key] = value

	# extract top 10
	top10 = OrderedDict()
	count = 0
	for key in sortedRes.keys():
		if count < 10 :
			top10[key] = sortedRes[key]
			count +=1
		else :
			break

	return top10

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

def getFlowCount(fileAddr, noOfSample, sampleFrequency) :
	c = CustomTimer(0, executeCommand, ["{0} -t {1} -r {2}".format(commandList['flowcount'], sampleFrequency, noOfSample)])	
	c.start()	
	writeTxtFile(c.join(), fileAddr)

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

def generateFileName(directory, pid, timeStamp) :
	fileName = directory + str(pid) + '_' + str(int(timeStamp)) + '.txt'
	return fileName

def getPerfStatSamples(input, directory):
	timeStamp = time.time()
	for process in psutil.process_iter():
		fileAddr = generateFileName(directory, process.pid, timeStamp)

		c = CustomTimer(0, executeCommand, ["{0} -e {1} sleep 0.01".format(commandList['perf stat'], ','.join(input["perf stat"]))])
		c.start()
		writeTxtFile(c.join(), fileAddr)

def getPerfStat(input, directory, noOfSample, sampleFrequency) :
	delay = 0
	while noOfSample > 0 :
		noOfSample -= 1
		threading.Timer(delay, getPerfStatSamples, [input, directory]).start()
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
			t1 = threading.Thread(target = targetFunction[key], args = (input, noOfSample, input['sampleFrequency'], ))
			t1.start()

		elif key == "commands":
			for cmd in input[key]:
				t2 = threading.Thread(target = targetFunction[cmd], args = (getFileAddr(cmd), noOfSample, input['sampleFrequency'], ))
				t2.start()

		elif key == "counters" :
			t3 = threading.Thread(target = targetFunction[key], args = (input, noOfSample, input['sampleFrequency'], ))
			t3.start()

		elif key == "perf stat" :
			createDirectory(input['outputDirectory'] + "/perf")
			createDirectory(input['outputDirectory'] + "/perf/stat")
			t4 = threading.Thread(target = targetFunction[key], args = (input, getFileAddr(key), noOfSample, input['sampleFrequency'], ))
			t4.start()

	t1.join()
	t2.join()
	t3.join()
	t4.join()

def zipOutput():

	path = '/root/aishu/psutil/output'

	files = []
	for r, d, f in os.walk(path):
	    for file in f:
	        files.append(os.path.join(r, file))

	# for file_name in files :
	# 	print(file_name) 

	with open("op.zip", "w") as zip:
		for f in files:
			zip.write(f)

	# with ZipFile("op.zip", "r") as zipFile :
	# 	zipFile.extractall(".")

def perfRecord(duration) :
	res = executeCommand("perf record sleep 2 > perf.data")

def isRecordDone():				# for now
	return True

def perfReport(outputDirectory, criticalThreads) :
	while isRecordDone() == False:
		continue
	top10Threads = [item[0] for item in criticalThreads.items()]

	createDirectory(outputDirectory + "/perf/report")

	for tid in top10Threads:
		fileName = generateFileName(getFileAddr("perf report"), tid, 1)
		res = executeCommand("perf report --call-graph=none --tid={0} > {1}".format(tid, fileName))
		

def main():

	input = loadData("input.json")
	# reset 
	clearDirectory(input['outputDirectory'])
	createDirectory(input['outputDirectory'])

	noOfSample = input["duration"] / input["sampleFrequency"]

	perfRecord(input["duration"])

 	collectStat(input, noOfSample)

 	# find critical threads
	criticalThreads = findCriticalThreads()
	print(criticalThreads)

	perfReport(input['outputDirectory'], criticalThreads)

	zipOutput()



if __name__ == "__main__":
	main()
