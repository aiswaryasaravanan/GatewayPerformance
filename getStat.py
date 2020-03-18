import psutil
import json
import os
import shutil
import commands
import subprocess
import time
import threading
from threading import _Timer
from collections import OrderedDict, defaultdict
import ast
import sys
import random
from zipfile import ZipFile
from prettytable import PrettyTable

def loadData(fileAddr):
	with open(fileAddr) as rObj:
		data = json.load(rObj)
	return data

files = {
	"all" : "tempResult/cpu/all.json",
	"edged" : "tempResult/cpu/edged.json",
	"dbus-daemon" : "tempResult/cpu/dbus-daemon.json",
	"handoff" : "tempResult/handoff.json",
	"flowcount" : "tempResult/flowcount.txt",
	"counters" : "tempResult/counters.json",
	"perf stat" : "tempResult/perf/stat/",
	"perfReport_cpu" : "tempResult/perf/report/cpu/",
	"perfReport_drops" : "tempResult/perf/report/drops/"
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

def getCpuPercent(proc, t):
   total_percent = proc.cpu_percent(interval = 0.1)
   total_time = sum(proc.cpu_times())
   return total_percent * ((t.system_time + t.user_time)/total_time)

def getThread(proc, thread) :
	try:
		threadEntry = {}
		threadEntry['tid'] = thread.id
		t = psutil.Process(thread.id)
		threadEntry['name'] = t.name()
		threadEntry['cpu_percent'] = getCpuPercent(proc, thread)
		threadEntry['user_time'] = thread.user_time
		threadEntry['system_time'] = thread.system_time

		# print("{0} {1} {2}".format(threadEntry['tid'], threadEntry['name'], threadEntry['cpu_percent']))

		return threadEntry
	except:
		pass

def getProcessSamples(proc) :
	sample = {}
	timeStamp = time.time()
	sample[timeStamp] = {}
	sample[timeStamp]['cpu_percent'] = proc.cpu_percent(interval = 0.1)
	sample[timeStamp]['threads'] = []

	for thread in proc.threads() :
		t = CustomTimer(0, getThread, [proc, thread])
		t.start()
		sample[timeStamp]['threads'].append(t.join())
	return sample

def findIndex(data, proc) :
	for index in range(len(data['all'])) :
		if proc.pid == data['all'][index]['pid'] :
			return index
	return -1

def collectNextProcessSample(input, lock) :
	for process in input["cpu"]:
		fileAddr = getFileAddr(process)
		with lock:
			data = loadData(fileAddr)

			if process == 'all' :
				for proc in psutil.process_iter():
					index = findIndex(data, proc)
					if(index != -1):
						t = CustomTimer(0, getProcessSamples, [proc])
						t.start()
						data[process][index]['samples'].append(t.join())
					else :
						newProcess = getProcessDetails(proc)
						t = CustomTimer(0, getProcessSamples, [proc])
						t.start()
						newProcess['samples'].append(t.join())
						data[process].append(newProcess)
			else :
				try:
					pid = data[process]["pid"]
					t = CustomTimer(0, getProcessSamples, [psutil.Process(pid)])
					t.start()
					data[process]['samples'].append(t.join())
				except:
					pass
				# for proc in psutil.process_iter():
				# 	if proc.name() == process:
				# 		data[process]['samples'].append(getProcessSamples(proc))
			writeFile(data, fileAddr)



def getProcessDetails(proc) :

	processEntry = OrderedDict()
	processEntry['pid'] = proc.pid
	processEntry['name'] = proc.name()
	processEntry['samples'] = []

	return processEntry

def getCpuProfile(input, noOfSample, sampleFrequency):

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
				try:
					if proc.name() == process:
						output[process] = getProcessDetails(proc)
						break
				except:
					print("process stopped unexpectedly")

		fileAddr = getFileAddr(process)
		writeFile(output, fileAddr)

	t = []

	delay = 0
	while noOfSample > 0 :
		noOfSample -= 1
		tObj = threading.Timer(delay, collectNextProcessSample, [input, lock])
		tObj.start()
		t.append(tObj)
		delay += sampleFrequency

	for tObj in t:
		tObj.join()

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

def findCriticalThreads_dropBased() :

	handoff = loadData(files["handoff"]) 
	handoff = poisonQueue(handoff)

	threadWithDrop = defaultdict(list)

	for ts in handoff["handoff"]:
		TS = ts.items()[0][0]
		for queue in ts[TS]['handoffq']:
			threadWithDrop[queue['tid']].append(queue['drops'])
	
	threadList = defaultdict(dict)
	for tid in threadWithDrop:
		threadList[tid] = {}
		threadList[tid]["avg"] = sum(threadWithDrop[tid]) / len(threadWithDrop[tid])
		threadList[tid]["incRate"] = threadWithDrop[tid][len(threadWithDrop[tid]) - 1] - threadWithDrop[tid][0]
		threadList[tid]["totalDrops"] = threadWithDrop[tid][len(threadWithDrop[tid]) - 1]
	
	sortedRes = OrderedDict()
	
	for key, value in sorted(threadList.items(), key = lambda item : item[1]["incRate"], reverse = True):
		sortedRes[key] = value

	return sortedRes

def findCriticalThreads_cpuBased() :

	data = loadData(getFileAddr("all"))
	threadWithCpuPercent = defaultdict(list)

	for process in data["all"] :
		for ts in process["samples"] :
			for thread in ts[ts.items()[0][0]]["threads"] :
				try:
					threadWithCpuPercent[thread["tid"]].append(thread["cpu_percent"])
				except:
					pass

	for key in threadWithCpuPercent :
		# print(str(key) + " - " + str(threadWithCpuPercent[key]))
		threadWithCpuPercent[key] = sum(threadWithCpuPercent[key]) / len(threadWithCpuPercent[key])

	sortedRes = OrderedDict()

	for key, value in sorted(threadWithCpuPercent.items(), key = lambda item : item[1], reverse = True):
		sortedRes[key] = value

	return sortedRes

def findCriticalThreads(key) :

	sortedRes = OrderedDict()

	if key == "cpu" :
		sortedRes = findCriticalThreads_cpuBased()
	elif key == "drops" :
		sortedRes = findCriticalThreads_dropBased()

	top10 = OrderedDict()
	count = 0
	for key in sortedRes.keys():
		if count < 10 :
			top10[key] = sortedRes[key]
			count +=1
		else :
			break
	return top10

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
			createDirectory('tempResult/' + key)
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
			createDirectory("tempResult/perf")
			createDirectory("tempResult/perf/stat")
			t4 = threading.Thread(target = targetFunction[key], args = (input, getFileAddr(key), noOfSample, input['sampleFrequency'], ))
			t4.start()

	t1.join()
	t2.join()
	t3.join()
	t4.join()

def perfRecord(duration) :
	res = executeCommand("perf record -s -F 999 -a --call-graph dwarf --sleep {0}".format(duration))

def isRecordDone():				# for now
	return True

def perfReport(criticalThreads, key, timeStamp) :
	while isRecordDone() == False:
		continue

	top10Threads = [item[0] for item in criticalThreads.items()]

	createDirectory("tempResult/perf/report")
	createDirectory("tempResult/perf/report/" + key)

	for tid in top10Threads:
		fileName = generateFileName(getFileAddr("perfReport_{0}".format(key)), tid, int(timeStamp))
		# res = executeCommand("perf report --tid={0} --stdio > {1}".format(tid, fileName))
		res = executeCommand("perf report --call-graph=none --tid={0} > {1}".format(tid, fileName))

def moveOutput(input, timeStamp):

	cwd = os.getcwd()

	try:
		os.chdir('/' + input['outputDirectory'])
	except:
		directories = input['outputDirectory'].split('/')
		os.chdir('/')
		for directory in directories :
			try:
				os.chdir(directory)
			except:
				os.mkdir(directory)
				os.chdir(directory)

	oldResult = commands.getoutput("find /{0} -maxdepth 1 -name 'result_*'".format(input['outputDirectory']))
	if oldResult and os.path.isdir(oldResult):
		shutil.rmtree(oldResult)

	os.rename('{0}/tempResult'.format(cwd), '/{0}/{1}'.format(input['outputDirectory'], "result_{0}".format(int(timeStamp))))

def checkAndDelete(input):
	availableZip = commands.getoutput("find /{0}/zippedResult -name 'result_*'".format(input['outputDirectory']))
	availableZip = (availableZip.split('\n'))
	availableZip.sort()
	if len(availableZip) == 10:
		commands.getoutput('rm {0}'.format(availableZip[0]))

def zipOutput(input, timeStamp):

	path = '/{0}/result_{1}'.format(input["outputDirectory"], int(timeStamp))

	if os.path.isdir('/{0}/zippedResult'.format(input['outputDirectory'])) :
		checkAndDelete(input)
	else:
		createDirectory('/{0}/zippedResult'.format(input['outputDirectory']))

	with ZipFile('/{0}/zippedResult/result_{1}.zip'.format(input["outputDirectory"], int(timeStamp)),'w') as zip:
		for root, directories, files in os.walk(path):
			for filename in files:
				filepath = os.path.join(root, filename)
				zip.write(filepath)
	# with ZipFile('/{0}/zippedResult/result_{1}.zip'.format(input["outputDirectory"], int(timeStamp)), "r") as zip:
	# 	zip.extractall()

def printTable(key, timeStamp, criticalThreads):
	table = PrettyTable(["tid", key, "perf report"])
	table.align['perf report'] = 'l'
	for tid in criticalThreads:
		report = ''
		with open('/root/psutil/tempResult/perf/report/{0}/{1}_{2}.txt'.format(key, tid, int(timeStamp)), 'r') as fObj:
			content = fObj.readlines()[8:-4]
			report = report.join(content)

		if key == "cpu":
			table.add_row([tid, criticalThreads[tid], report])
		elif key =="drops":
			table.add_row([tid, str(criticalThreads[tid]['incRate']) + '(' + str(criticalThreads[tid]['totalDrops']) + ')', report])
	print(table)	

def main():

	input = loadData("input.json")
	noOfSample = input["duration"] / input["sampleFrequency"]
	print("Potential root cause")

	while True:
		timeStamp = time.time()	
		createDirectory("/root/psutil/tempResult")
		os.chdir("/root/psutil")

		perfRecord(input["duration"])
 		collectStat(input, noOfSample)

 		# find critical threads
		criticalThreads = findCriticalThreads("drops")
		perfReport(criticalThreads, "drops", timeStamp)
		printTable("drops", timeStamp, criticalThreads)

		criticalThreads = findCriticalThreads("cpu")
		perfReport(criticalThreads, "cpu", timeStamp)
		printTable("cpu", timeStamp, criticalThreads)

		moveOutput(input, timeStamp)
		zipOutput(input, timeStamp)

		if input['auto mode'] == 0 :
			break

if __name__ == "__main__":
	main()
