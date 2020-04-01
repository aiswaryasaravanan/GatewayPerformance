import utils
import os
import time
import subprocess

def doPerfRecord() :
    utils.createDirectory('tempResult/perf')
    # res = utils.executeCommand("perf record -s -F 999 -a --call-graph dwarf -- sleep 3 > tempResult/perf/perf.data")
    sts = subprocess.Popen("perf record -s -F 999 -a --call-graph dwarf -- sleep 100 > tempResult/perf/perf.data &", shell = True)
    # os.rename('perf.data', 'tempResult/perf/perf.data')
    # time.sleep(3)        # as of now
    # return sts.pid

def doStat(events, directory, tid):
    fileName = utils.generateFileName(directory, str(tid))
    c = utils.CustomTimer(0, utils.executeCommand, ["{0} -e {1} -t {2} sleep 0.01".format(utils.getCommandList('perf stat'), ','.join(events), tid)])
    c.start()
    utils.writeTxtFile(c.join(), fileName)

def collectPerfStat(events, criticalItems) :
    for key in criticalItems:
        if key != 'counters':
            directory = '{0}/{1}'.format(utils.getFileAddr('perf stat'), key)
            utils.createDirectory(directory)
            for tid in criticalItems[key]:
                doStat(events, directory, tid)
                
def doReport(directory, tid):
    fileName = utils.generateFileName(directory, str(tid))
    # res = executeCommand("perf report --tid={0} --stdio > {1}".format(tid, fileName))
    res = utils.executeCommand("perf report --call-graph=none --tid={0} -i 'tempResult/perf/perf.data' > {1}".format(tid, fileName))

def collectPerfReport(criticalItems):    
    wait = 0                    
    while utils.executeCommand("ps aux | grep 'perf record' | grep -v grep | awk '{print $2}'"):
        if wait >= 15:
            print('killing')
            utils.executeCommand('kill -9 {0}'.format(utils.executeCommand("ps aux | grep 'perf record' | grep -v grep | awk '{print $2}'")))
            exit()
            
        wait += 1
        time.sleep(1)
        print('waiting for perf record to complete...')
        continue

    for key in criticalItems:
        if key != 'counters':
            directory = '{0}/{1}'.format(utils.getFileAddr('perf report'), key)
            utils.createDirectory(directory)
            for tid in criticalItems[key]:
                doReport(directory, tid)
                