import os
import shutil
import json
import commands
from zipfile import ZipFile
from threading import _Timer
from prettytable import PrettyTable

import random
import globalVariable

files = {
    "all" : "tempResult/cpu/all.json",
    "edged" : "tempResult/cpu/edged.json",
    "dbus-daemon" : "tempResult/cpu/dbus-daemon.json",
    "handoff" : "tempResult/commands/handoff.json",
    "counters" : "tempResult/counters.json",
    "perf stat" : "tempResult/perf/stat",
    "perf report" : "tempResult/perf/report"
}

commandList = {
    "handoff" : "debug.py -v --handoff ",
    "counters" : "getcntr -c",
    "perf stat" : "perf stat"
}

def getTargetFunction(targetFunction, key):
    if not targetFunction.has_key(key):
        targetFunction.setdefault(key, getCustomCommands)
    return targetFunction[key]

def getCustomCommands(fileName, command, noOfSample, sampleFrequency, lock):
    commandOutput = executeCommand('{0} > {1}'.format(getCommandList(command['name']), fileName))

class CustomTimer(_Timer):
    def __init__(self, interval, function, args=[], kwargs={}):
        self._original_function = function
        super(CustomTimer, self).__init__(interval, self._do_execute, args, kwargs)

    def _do_execute(self, *a, **kw):
        self.result = self._original_function(*a, **kw)

    def join(self):
        super(CustomTimer, self).join()
        return self.result

def createDirectory(directory) :
    try :
        os.mkdir(directory)
    except :
        if os.path.exists(directory):                            # File exists
            pass
        else :                                                   # No such file or directory 
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
    return key                         # for custom commands

def executeCommand(command) :
    result = commands.getoutput(command)
    return result

def generateFileName(directory, pid) :
    fileName = directory + '/' + str(pid) + '.txt'
    return fileName

def getNoOfSample(sampleFrequency, duration):
    noOfSample = (duration / sampleFrequency) + 1
    return noOfSample

def deleteTemporaryFiles():
    # clearDirectory('diagDump_{0}'.format(timeStamp))
    clearDirectory('tempResult')
    globalVariable.isTriggered = False          # reset
    
def isFileExists(fileName, directory):
    if os.path.exists('tempResult/perf') and executeCommand('find {0} -name {1}'.format(directory, fileName)):
        return 1
    return 0

def modifyDrop(drop) :
    drop += random.randint(1, 1000)
    return drop

def checkAndDelete(outputDirectory, windowSize):
    availableZip = executeCommand("find {0} -maxdepth 1 -name '*.zip'".format(outputDirectory))
    availableZip = (availableZip.split('\n'))
    availableZip.sort()
    if len(availableZip) >= windowSize:
        sts = executeCommand('rm {0}'.format(availableZip[0]))

def zipOutput(outputDirectory, timeStamp):
    # moveDirectory('{0}/tempResult'.format(outputDirectory), '{0}/diagDump_{1}'.format(outputDirectory, timeStamp))
    # path = '{0}/diagDump_{1}'.format(outputDirectory, timeStamp)
    path = 'tempResult'

    checkAndDelete(outputDirectory, globalVariable.windowSize)

    with ZipFile('/{0}/diagDump_{1}.zip'.format(outputDirectory, timeStamp),'w') as zip:
        for root, directories, files in os.walk(path):
            for filename in files:
                filepath = os.path.join(root, filename)
                zip.write(filepath)

def unZipOutput(filename, outputDirectory):
    with ZipFile(filename, "r") as zip:
        zip.extractall()
        
def createSummary(criticalItems):
    print('\n\tSummary Report\n')
    for key in criticalItems:
        count = 0 
        table = PrettyTable()
        fields = []
        print(key)
        if key == 'cpu':
            fields = ['Thread Name', key]
            for tid in criticalItems[key]:
                if count > 3:
                    break
                table.add_row([criticalItems[key][tid]['name'], sum(criticalItems[key][tid]['cpuPercent']) / len(criticalItems[key][tid]['cpuPercent'])])
                count += 1
        elif key == 'drops':
            ['Handoff Queue Name', key]
            for tid in criticalItems[key]:
                if count > 3:
                    break
                increaseRate = criticalItems[key][tid]['drops'][len(criticalItems[key][tid]['drops']) - 1] - criticalItems[key][tid]['drops'][0]
                totalDrops = criticalItems[key][tid]['drops'][len(criticalItems[key][tid]['drops']) - 1]
                table.add_row([criticalItems[key][tid]['name'], str(increaseRate) + '(' + str(totalDrops) + ')'])
                count += 1
        elif key == 'counters':
            fields = ['Counter Name', 'drops']
            for name in criticalItems[key]:
                if count > 3:
                    break
                increaseRate = criticalItems[key][name][len(criticalItems[key][name]) - 1] - criticalItems[key][name][0]
                totalDrops = criticalItems[key][name][len(criticalItems[key][name]) - 1]
                table.add_row([name, str(increaseRate) + '(' + str(totalDrops) + ')'])
                count += 1
        alignTable(table, fields, 'l')
        print(table)
        del table
        
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


