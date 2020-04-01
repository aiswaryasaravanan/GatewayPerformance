import utils
import time

import globalVariable
import perf

class Counters:
    
    def __init__(self):
        pass
    
    def __getDpdkInterfaceNames(self):
        dpdkPortsDump = utils.executeCommand('debug.py -v --dpdk_ports_dump')
        dpdkPortsDump = eval(dpdkPortsDump)
        dpdkInterfaceNames = []
        for dump in dpdkPortsDump:
            dpdkInterfaceNames.append(dump['name'])
        return dpdkInterfaceNames

    def __getCounterSamples(self, counters, triggerLock):
        dpdkInterfaceNames = self.__getDpdkInterfaceNames()
        countersList = {}
        for name in dpdkInterfaceNames:
            countersList['dpdk_{0}_pstat_ierrors'.format(name)] = utils.executeCommand('{0} dpdk_{1}_pstat_ierrors'.format(utils.getCommandList('counters'), name))
            countersList['dpdk_{0}_pstat_oerrors'.format(name)] = utils.executeCommand('{0} dpdk_{1}_pstat_oerrors'.format(utils.getCommandList('counters'), name))
            countersList['dpdk_{0}_pstat_imissed'.format(name)] = utils.executeCommand('{0} dpdk_{1}_pstat_imissed'.format(utils.getCommandList('counters'), name))

        for cntr in counters:
            c = utils.CustomTimer(0, utils.executeCommand, ["{0} {1}".format(utils.getCommandList('counters'), cntr['name'])])        # actual
            c.start()
            countersList[cntr['name']] = c.join()
            
        return countersList

    def getCounters(self, counters, noOfSample, sampleFrequency, triggerLock) :
        output = {}
        output["counters"] = []

        delay = 0
        while noOfSample > 0 :
            noOfSample -= 1
            sample = {}
            
            c = utils.CustomTimer(delay, self.__getCounterSamples, [counters, triggerLock])
            c.start()

            sample[time.time()] = c.join()
            output['counters'].append(sample)
            delay = sampleFrequency                        # for now
            
            # with triggerLock:
            #     if globalVariable.autoMode and globalVariable.isTriggered == 0:
            #         outputPoisoned = Counters.Counters.poisonCounters(output)

            #         index = len(outputPoisoned['counters']) - 1
            #         TS = outputPoisoned['counters'][index]
            #         for counter in TS[TS.items()[0][0]]:
            #             if counter.has_key('trigger'):
            #                 if counter['trigger'] >= counter['trigger']:
            #                     print('triggered - > counter')
            #                     perf.doPerfRecord()
            #                     isTriggered = 1

        fileAddr = utils.getFileAddr("counters")
        utils.writeFile(output, fileAddr)
        
    @staticmethod
    def poisonCounters(counters) :
        flag = 1
        for TS in counters['counters']:
            if flag :
                pre = TS
                flag = 0
                continue

            for counter in TS[TS.items()[0][0]]:
                TS[TS.items()[0][0]][counter] = utils.modifyDrop(int(pre[pre.items()[0][0]][counter]))
            pre = TS

        # utils.writeFile(counters, utils.getFileAddr('counters'))
        return counters