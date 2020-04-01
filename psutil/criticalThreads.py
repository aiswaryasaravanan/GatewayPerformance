import utils
from collections import OrderedDict, defaultdict

import Counters
import Handoff

def getTop10(data):
    top10 = OrderedDict()
    count = 0
    for key in data.keys():
        if count < 10 :
            top10[key] = data[key]
            count +=1
        else :
            break
    return top10

def counterBasedCriticalItems():
    counters = utils.loadData(utils.getFileAddr('counters'))
    counters = Counters.Counters.poisonCounters(counters)

    criticalItems = defaultdict()

    for TS in counters['counters']:
        for counter in TS[TS.items()[0][0]]:
            drop = TS[TS.items()[0][0]][counter]
            if not criticalItems.has_key(counter):
                criticalItems[counter] = []
            criticalItems[counter].append(int(drop))

    sortedRes = OrderedDict()
    for key, value in sorted(criticalItems.items(), key = lambda item : item[1][len(item[1]) - 1] - item[1][0], reverse =True):
        sortedRes[key] = value

    return getTop10(sortedRes)

def dropBasedCriticalItems():
    handoff = utils.loadData(utils.getFileAddr("handoff")) 
    handoff = Handoff.Handoff.poisonQueue(handoff)

    criticalItems = defaultdict(dict)

    for ts in handoff["handoff"]:
        TS = ts.items()[0][0]
        for queue in ts[TS]['handoffq']:
                criticalItems[queue['tid']]['name'] = queue['name']        # TODO : has_key()
                if not criticalItems[queue['tid']].has_key('drops') :
                    criticalItems[queue['tid']]['drops'] = []                
                criticalItems[queue['tid']]['drops'].append(queue['drops'])

    sortedRes = OrderedDict()
    
    for key, value in sorted(criticalItems.items(), key = lambda item : item[1]['drops'][len(criticalItems[item[0]]['drops']) - 1] - item[1]['drops'][0], reverse = True):
        sortedRes[key] = value

    return getTop10(sortedRes)

def cpuBasedCriticalItems():
    data = utils.loadData(utils.getFileAddr("all"))
    criticalItems = defaultdict(dict)

    for process in data["all"] :
        if process.has_key('samples'):
            for ts in process["samples"] :
                for thread in ts[ts.items()[0][0]]["threads"] :
                    criticalItems[thread['tid']]['name'] = thread['name']
                    if not criticalItems[thread["tid"]].has_key('cpuPercent') :
                        criticalItems[thread["tid"]]['cpuPercent'] = []
                    criticalItems[thread["tid"]]['cpuPercent'].append(thread["cpu_percent"])

    sortedRes = OrderedDict()

    for key, value in sorted(criticalItems.items(), key = lambda item : sum(item[1]['cpuPercent']) / len(item[1]['cpuPercent']), reverse = True):
        sortedRes[key] = value

    return getTop10(sortedRes)

def extractCriticalItems(input):
    criticalItems = defaultdict(dict)
    criticalItems['cpu'] = cpuBasedCriticalItems()
    criticalItems['drops'] = dropBasedCriticalItems()
    criticalItems['counters'] = counterBasedCriticalItems()
    return criticalItems