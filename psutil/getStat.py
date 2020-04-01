import argparse
import threading
from collections import defaultdict, OrderedDict
import subprocess
import time
import os

import CpuProfile
import Handoff
import Counters
import utils
import manifest
import criticalThreads
import perf
import globalVariable

def parseCommandLineArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-F", "--filename", help="output zip file", type = file)
    args = parser.parse_args()
    return vars(args)
    
def getDiagDump(input, noOfSample, targetFunction):
    triggerLock = threading.Lock()
    for key in input.keys():
        if key == "cpu":
            utils.createDirectory('tempResult/{0}'.format(key))
            t1 = threading.Thread(target = utils.getTargetFunction(targetFunction, key), args = (input['cpu'], noOfSample, input['sampleFrequency'], triggerLock, ))
            t1.start()

        elif key == "commands":
            utils.createDirectory('tempResult/{0}'.format(key))
            for cmd in input[key]:
                commandName = cmd['name']
                t2 = threading.Thread(target = utils.getTargetFunction(targetFunction, commandName), args = (utils.getFileAddr(commandName), cmd, noOfSample, input['sampleFrequency'], triggerLock, ))
                t2.start()

        elif key == "counters" :
            t3 = threading.Thread(target = utils.getTargetFunction(targetFunction, key), args = (input['counters'], noOfSample, input['sampleFrequency'], triggerLock, ))
            t3.start()

    t1.join()
    t2.join()
    t3.join()
            
def main():
    
    cpu = CpuProfile.CpuProfile()
    handoff = Handoff.Handoff()
    counter = Counters.Counters()
    
    targetFunction = {
        "cpu" : cpu.getCpuProfile,
        "handoff" : handoff.getHandoff,
        "counters" : counter.getCounters,
    }
    
    input = utils.loadData("input.json")    
    utils.clearDirectory('tempResult')
    utils.createDirectory(input['outputDirectory'])
    
    globalVariable.autoMode = input.has_key('auto mode')
    
    argDict = parseCommandLineArguments()

    if argDict.items()[0][1] != None:            # cmdline arg is there
        timeStamp = time.time()
        utils.unZipOutput(argDict.items()[0][1], input['outputDirectory'])
        criticalItems = criticalThreads.extractCriticalItems(input)
        perf.collectPerfReport(criticalItems)
        perf.collectPerfStat(input['perf stat'], criticalItems)
        utils.createSummary(criticalItems)
        utils.printTable(criticalItems)
        utils.deleteTemporaryFiles()            
        pass

    else:
        consecutiveThresholdExceedLimit = 0
        while True:

            utils.createDirectory('tempResult')
            timeStamp = time.time()

            noOfSample = utils.getNoOfSample(input['sampleFrequency'], input['duration'])

            getDiagDump(input, noOfSample, targetFunction)
            manifest.createManifest()

            criticalItems = criticalThreads.extractCriticalItems(input)

            if not globalVariable.autoMode:
                perf.doPerfRecord()

            perf.collectPerfReport(criticalItems)
            perf.collectPerfStat(input['perf stat'], criticalItems)

            utils.createSummary(criticalItems)
            utils.printTable(criticalItems)

            utils.zipOutput(input['outputDirectory'], timeStamp)
            utils.deleteTemporaryFiles()

            if not globalVariable.autoMode :
                break

            consecutiveThresholdExceedLimit += 1
            if consecutiveThresholdExceedLimit == input['auto mode']['consecutiveThresholdExceedLimit'] :
                break
        

if __name__ == "__main__" :
    main()
