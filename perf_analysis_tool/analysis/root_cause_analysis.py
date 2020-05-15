import sys
sys.path.append('perf_analysis_tool')
import time
from collections import OrderedDict, defaultdict

import utils
from diag.perf.perf_globals import PerfGlobals
        
def get_dict(critical_items, key, *argv):
    if not critical_items.has_key(key):
        critical_items[key] = {}
        if len(argv)==2:
            critical_items[key]['name'] = argv[1]
        critical_items[key]['value'] = []
    critical_items[key]['value'].append(argv[0])

def counter_based_critical_items():
    from monitor.counter_monitor import CounterMonitor
    
    critical_items = defaultdict()
    counters = utils.load_data(utils.get_file_addr(CounterMonitor.files, "counters"))

    for entry in counters:
        for counter in entry['counters']:
            get_dict(critical_items, counter['name'], counter['drops'])

    sorted_res = OrderedDict()

    for key, value in sorted(critical_items.items(), key = lambda item : utils.get_total_drops(item[1]['value']), reverse =True):
        sorted_res[key] = value

    return utils.get_top_10(sorted_res)

def drop_based_critical_items():
    from monitor.command_monitor import Commands
    handoff = utils.load_data(utils.get_file_addr(Commands.files, "handoff")) 

    critical_items = defaultdict(dict)
    
    for entry in handoff:
        for queue in entry['handoffq']:
            get_dict(critical_items, queue['tid'], queue['drops'], queue['name'])

    sorted_res = OrderedDict()
    
    for key, value in sorted(critical_items.items(), key = lambda item : utils.get_total_drops(item[1]['value']), reverse = True):
        sorted_res[key] = value

    return utils.get_top_10(sorted_res)

def cpu_based_critical_items():
    from monitor.cpu_monitor import CpuMonitor
    data = utils.load_data(utils.get_file_addr(CpuMonitor.files, "all"))
    critical_items = defaultdict(dict)

    for process in data: 
        for sample in process['samples']:
            for thread in sample['threads']:
                get_dict(critical_items, thread['tid'], thread['cpu_percent'], thread['name'])

    sorted_res = OrderedDict()

    for key, value in sorted(critical_items.items(), key = lambda item : utils.get_average(item[1]['value']), reverse = True):
        sorted_res[key] = value

    return utils.get_top_10(sorted_res)

def extract_critical_items(analysis_list):
    critical_items = OrderedDict()
    for category in analysis_list:
        if category == 'cpu':
            critical_items['cpu'] = cpu_based_critical_items()
        elif category == 'handoff_drops':
            critical_items['drops'] = drop_based_critical_items()
        elif category == 'counters':
            critical_items['counters'] = counter_based_critical_items()
                
    return critical_items

def extract_top_latency():
    latency_processed = {}
    fields = ['Switches', 'Runtime', 'Average delay', 'Maximum delay']
    latency_data = {}
    for cnt in range(PerfGlobals.number_of_sched):
        latency_file = '{0}/perf_latency_{1}.txt'.format(utils.get_file_addr(PerfGlobals.directories, 'latency'), cnt+1)
        get_latency_data(latency_file, latency_data, fields)
    for key in PerfGlobals.latency_key:
        latency_processed[key] = sort_latency_data(latency_data, key, fields)
    return latency_processed
        
def get_latency_data(input_file, latency_data, fields):
    data = utils.read_file(input_file, 4, -4)
    for line in data:
        line = line.strip().split()
        tid = line[PerfGlobals.latency_field_index['Tid']]
        if not latency_data.has_key(tid):
            latency_data[tid] = {}
            for field in fields:
                latency_data[tid][field] = []
        for field in fields:
            latency_data[tid][field].append(float(line[PerfGlobals.latency_field_index[field]]))
    return latency_data

def sort_latency_data(latency_data, key, fields):
    sorted_res = OrderedDict()
    for key, value in sorted(latency_data.items(), key = lambda item : utils.get_average(item[1][key]) , reverse = True):
        sorted_res[key] = latency_data[key]
    return utils.get_top_10(sorted_res)