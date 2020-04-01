import utils
import os
import time
import subprocess
import globalVariable

def doPerfRecord() :
    utils.createDirectory('tempResult/perf')
    FNULL = open(os.devnull, 'w')
    for cnt in range(globalVariable.recordCount):
        sts = subprocess.Popen("perf record -s -F 999 -a --call-graph dwarf -o perf{0}.data -- sleep 10 &".format(cnt+1), shell = True, stdout = FNULL, stderr = subprocess.STDOUT)
        time.sleep(5)       # on pupose
    # sts = subprocess.Popen("perf record -s -F 999 -a --call-graph dwarf -o perf2.data -- sleep 10 &", shell = True, stdout = FNULL, stderr = subprocess.STDOUT)
   
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
                
def doReport(directory, inputFile, tid):
    fileName = utils.generateFileName(directory, str(tid))
    # res = executeCommand("perf report --tid={0} --stdio > {1}".format(tid, fileName))
    res = utils.executeCommand("perf report --call-graph=none --tid={0} -i {1} > {2}".format(tid, inputFile, fileName))
    
def fun(directory, inputFile, key, criticalItems):
    directory = '{0}/{1}'.format(directory, key)
    utils.createDirectory(directory)
    for tid in criticalItems[key]:
        doReport(directory, inputFile, tid)
                

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
    
    for cnt in range(globalVariable.recordCount):
        os.rename('perf{0}.data'.format(cnt+1), 'tempResult/perf/perf{0}.data'.format(cnt+1))
        # os.rename('perf2.data', 'tempResult/perf/perf2.data')
    
    for key in criticalItems:
        if key != 'counters':
            for cnt in range(globalVariable.recordCount):
                fun(utils.getFileAddr('perf report') + str(cnt + 1), 'tempResult/perf/perf{0}.data'.format(cnt + 1), key, criticalItems)
                # fun(utils.getFileAddr('perf report2'), 'tempResult/perf/perf2.data', key, criticalItems)
            