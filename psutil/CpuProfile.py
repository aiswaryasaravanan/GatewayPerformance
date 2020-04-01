import psutil
import threading
import utils
from collections import OrderedDict
import time
import globalVariable
import perf

class CpuProfile:
    def __init__(self):
        pass
                    
    def __getCpuPercent(self, proc, t):
        total_percent = proc.cpu_percent(interval = 0.1)
        total_time = sum(proc.cpu_times())
        return total_percent * ((t.system_time + t.user_time)/total_time)

    def __getThread(self, proc, thread, process, triggerLock) :

        threadEntry = {}
        threadEntry['tid'] = thread.id

        t = psutil.Process(thread.id)
        threadEntry['name'] = t.name()
        try:
            threadEntry['cpu_percent'] = self.__getCpuPercent(proc, thread)
        except:
            threadEntry['cpu_percent'] = 0.0    
        threadEntry['user_time'] = thread.user_time
        threadEntry['system_time'] = thread.system_time   
        
        with triggerLock: 
            if globalVariable.autoMode and globalVariable.isTriggered == 0:
                if process.has_key('trigger'):
                    if threadEntry['cpu_percent'] >= process['trigger']:
                        perf.doPerfRecord()
                        globalVariable.isTriggered = 1
                
        return threadEntry
    

    def __getProcessSamples(self, proc, process, triggerLock) :
        sample = {}
        timeStamp = time.time()
        sample[timeStamp] = {}
        sample[timeStamp]['cpu_percent'] = proc.cpu_percent(interval = 0.1)
        # sample[timeStamp]['threads'] = []

        threadObjects = []
        for thread in proc.threads() :
            if not sample[timeStamp].has_key('thread'):
                sample[timeStamp]['threads'] = []
            t = utils.CustomTimer(0, self.__getThread, [proc, thread, process, triggerLock])
            t.start()
            threadObjects.append(t)
            
        for t in threadObjects:
            sample[timeStamp]['threads'].append(t.join())

        return sample

    def __getProcessDetails(self, proc) :
        processEntry = OrderedDict()

        try:
            processEntry['pid'] = proc.pid
            processEntry['name'] = proc.name()
            processEntry['samples'] = []
        except:
            pass
        return processEntry
    
    def __findIndex(self, data, proc) :
        for index in range(len(data['all'])) :
            if proc.pid == data['all'][index]['pid'] :
                return index
        return -1

    def __collectNextProcessSample(self, cpu, cpuSamplingLock, triggerLock) :
        for process in cpu:
            processName = process['name']
            fileAddr = utils.getFileAddr(processName)

            with cpuSamplingLock:
                data = utils.loadData(fileAddr)

                if processName == 'all' :
                    for proc in psutil.process_iter():
                        index = self.__findIndex(data, proc)
                        if(index == -1):
                            data[processName].append(self.__getProcessDetails(proc))
                            index = len(data['all']) - 1
                        data[processName][index]['samples'].append(self.__getProcessSamples(proc, process, triggerLock))
                else :
                    try:
                        pid = data[processName]["pid"]
                        data[processName]['samples'].append(self.__getProcessSamples(psutil.Process(pid), process, triggerLock))
                    except:
                        pass
                utils.writeFile(data, fileAddr)
                
    def getCpuProfile(self, cpu, noOfSample, sampleFrequency, triggerLock):                    # making a room for process
        cpuSamplingLock = threading.Lock()
        
        for process in cpu:
            processName = process['name']
            output = {}
            if processName == 'all' :
                output[processName] = []
                for proc in psutil.process_iter():
                    output[processName].append(self.__getProcessDetails(proc))
            else :
                output[processName] = {}
                for proc in psutil.process_iter():
                    if proc.name() == processName:
                        output[processName] = self.__getProcessDetails(proc)
                        break

            fileAddr = utils.getFileAddr(processName)
            utils.writeFile(output, fileAddr)

        threadObjects = []
        delay = 0
        while noOfSample > 0 :
            tObj = threading.Timer(delay, self.__collectNextProcessSample, [cpu, cpuSamplingLock, triggerLock])
            tObj.start()
            threadObjects.append(tObj)
            delay += sampleFrequency
            noOfSample -= 1

        for tObj in threadObjects:
            tObj.join()
    
