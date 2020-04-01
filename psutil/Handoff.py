import utils
import time
import random
import globalVariable
import perf

class Handoff:
    def __init__(self):
        pass
    
    def getHandoff(self, fileAddr, command, noOfSample, sampleFrequency, triggerLock) :
        
        output = {}
        output['handoff'] = []

        delay = 0
        while noOfSample > 0 :

            noOfSample -= 1
            sample = {}
            c = utils.CustomTimer(delay, utils.executeCommand, [utils.getCommandList(command['name'])])        
            c.start()
            timeStamp = time.time()
            entry = {}
            entry = c.join()
            sample[timeStamp] = eval(entry)
            output['handoff'].append(sample)
            delay = sampleFrequency
            
            with triggerLock:
                if globalVariable.autoMode and globalVariable.isTriggered == 0:
                    outputPoisoned = Handoff.poisonQueue(output)

                    index = len(outputPoisoned['handoff']) - 1
                    TS = outputPoisoned['handoff'][index]
                    for queue in TS[TS.items()[0][0]]['handoffq']:
                        if queue['drops'] >= command['trigger']:
                            perf.doPerfRecord()
                            globalVariable.isTriggered = 1
                            break

        utils.writeFile(output, fileAddr)
        
    @staticmethod
    def poisonQueue(handoff) :
        flag = 1
        for ts in handoff["handoff"] :
            if flag :
                pre = ts
                flag = 0
                continue

            for queue in range(len(ts[ts.items()[0][0]]["handoffq"])) :
                ts[ts.items()[0][0]]["handoffq"][queue]["drops"] = utils.modifyDrop(pre[pre.items()[0][0]]["handoffq"][queue]["drops"])
            pre = ts

        # utils.writeFile(handoff, utils.getFileAddr('handoff'))
        return handoff
    

