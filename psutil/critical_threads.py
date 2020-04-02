import utils
from collections import OrderedDict, defaultdict

import Counters
import Handoff

def get_top_10(data):
    top_10 = OrderedDict()
    count = 0
    for key in data.keys():
        if count < 10 :
            top_10[key] = data[key]
            count +=1
        else :
            break
    return top_10

def counter_based_critical_items():
    counters = utils.load_data(utils.get_file_addr('counters'))
    counters = Counters.Counters.poison_counters(counters)

    critical_items = defaultdict()

    for TS in counters['counters']:
        for counter in TS[TS.items()[0][0]]:
            drop = TS[TS.items()[0][0]][counter]
            if not critical_items.has_key(counter):
                critical_items[counter] = []
            critical_items[counter].append(int(drop))

    sorted_res = OrderedDict()
    for key, value in sorted(critical_items.items(), key = lambda item : item[1][len(item[1]) - 1] - item[1][0], reverse =True):
        sorted_res[key] = value

    return get_top_10(sorted_res)

def drop_based_critical_items():
    handoff = utils.load_data(utils.get_file_addr("handoff")) 
    handoff = Handoff.Handoff.poison_queue(handoff)

    critical_items = defaultdict(dict)

    for ts in handoff["handoff"]:
        TS = ts.items()[0][0]
        for queue in ts[TS]['handoffq']:
                critical_items[queue['tid']]['name'] = queue['name']        # TODO : has_key()
                if not critical_items[queue['tid']].has_key('drops') :
                    critical_items[queue['tid']]['drops'] = []                
                critical_items[queue['tid']]['drops'].append(queue['drops'])

    sorted_res = OrderedDict()
    
    for key, value in sorted(critical_items.items(), key = lambda item : item[1]['drops'][len(critical_items[item[0]]['drops']) - 1] - item[1]['drops'][0], reverse = True):
        sorted_res[key] = value

    return get_top_10(sorted_res)

def cpu_based_critical_items():
    data = utils.load_data(utils.get_file_addr("all"))
    critical_items = defaultdict(dict)

    for process in data["all"] :
        if process.has_key('samples'):
            for ts in process["samples"] :
                for thread in ts[ts.items()[0][0]]["threads"] :
                    critical_items[thread['tid']]['name'] = thread['name']
                    if not critical_items[thread["tid"]].has_key('cpu_percent') :
                        critical_items[thread["tid"]]['cpu_percent'] = []
                    critical_items[thread["tid"]]['cpu_percent'].append(thread["cpu_percent"])

    sorted_res = OrderedDict()

    for key, value in sorted(critical_items.items(), key = lambda item : sum(item[1]['cpu_percent']) / len(item[1]['cpu_percent']), reverse = True):
        sorted_res[key] = value

    return get_top_10(sorted_res)

def extract_critical_items(input):
    critical_items = defaultdict(dict)
    critical_items['cpu'] = cpu_based_critical_items()
    critical_items['drops'] = drop_based_critical_items()
    critical_items['counters'] = counter_based_critical_items()
    return critical_items