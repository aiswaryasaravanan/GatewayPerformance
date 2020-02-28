import psutil
import json
# import os
import commands
import subprocess
import sched
import time

def getProcessDetails(proc):
	
	processEntry = proc.as_dict(attrs = ['name'])

	processEntry['cpuPercent'] = proc.cpu_percent(interval = 0.01)
	
	threads = {}
	for thread in proc.threads() :
		threads[thread.id] = {}
		threads[thread.id]['user_time'] = thread.user_time
		threads[thread.id]['system_time'] = thread.system_time
		
	processEntry["threads"] = threads
	return processEntry


def readInput():
	with open("input.json") as rObj:
		input = json.load(rObj)
		return input

def dumpOutput(output):
	with open("output.json", "w") as wObj:
                json.dump(output, wObj, indent = 4, sort_keys = True)

def collectStat(input):

	output = {}
	for key in input.keys():
	
		if key == "duration" or key == "sampleFrequency":	#for now
			continue

		output[key] = {}

		if key == "cpu":
			
			for process in input[key]:

				if process == "root" :
					output[key][process] = {} 
					for proc in psutil.process_iter():
						output[key][process][proc.pid] = getProcessDetails(proc) 
				else :
					for proc in psutil.process_iter():
						if proc.name() == process:
							output[key][proc.pid] = getProcessDetails(proc)
					
	
		elif key == "commands":
		
			index = 0
			for cmd in input[key]:
				
				if isinstance(cmd, dict) :
					for val in cmd.keys() :
						output[key][val] = {}

						if val == "getcntr":
							for cntr in input[key][index][val] :
								temp = commands.getstatusoutput('getcntr -c ' + cntr)
								output[key][val][cntr] = temp[1]

				else :
					if cmd == "handoff":
						output[key][cmd] = subprocess.check_output(['debug.py', '-v', '--handoff']) 
	
				index += 1	

	return output



def main():

	input = readInput()
	output = {}

	# s = sched.scheduler(time.time, time.sleep)

	# noOfSample = input["duration"] / input["sampleFrequency"]
	# print(noOfSample)

	# for sample in range(noOfSample):

	# 	# output[sample] = collectStat(input)
	
	# 	delay = 0
	# 	output[sample] = s.enter(delay, 1, collectStat, argument=(input, ))			#problem returning
	# 	delay += input["sampleFrequency"]
	# s.run()

	output = collectStat(input)
		
	dumpOutput(output)


if __name__ == "__main__":
	main()
