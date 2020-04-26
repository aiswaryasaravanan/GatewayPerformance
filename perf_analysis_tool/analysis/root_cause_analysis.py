import sys
sys.path.append('perf_analysis_tool')

from collections import OrderedDict, defaultdict

import utils
import global_variable
from monitor.counter_monitor import CounterMonitor
from monitor.command_monitor import Commands
from monitor.cpu_monitor import CpuMonitor
from diag.perf.perf_diag import PerfDiag
from diag.perf.perf_globals import PerfGlobals

def do_perf_diag(critical_items):
    if not global_variable.auto_mode:
        for count in range(PerfGlobals.number_of_record):
            output_file = 'perf_record_{0}.data'.format(count+1)
            PerfDiag.do_perf_record(output_file)
        for count in range(PerfGlobals.number_of_sched):
            output_file = 'perf_sched_{0}.data'.format(count+1)
            PerfDiag.do_perf_sched(output_file)
            
    report_util(critical_items)
    stat_util(critical_items)
    latency_analysis = latency_util()
    critical_items.update(latency_analysis)
    
    return critical_items

def report_util(critical_items):
    if PerfDiag.process_exiting_check('record'):
        for cnt in range(PerfGlobals.number_of_record):
            source_file = 'perf_record_{0}.data'.format(cnt+1)
            destination = '{0}/{1}'.format(utils.get_file_addr(PerfGlobals.directories, 'record'), source_file)
            utils.rename_file(source_file, destination)
        
        for key in critical_items:
            if key != 'counters':
                for cnt in range(PerfGlobals.number_of_record):
                    directory = '{0}/report{1}/{2}'.format(utils.get_file_addr(PerfGlobals.directories, 'report'), str(cnt + 1), key)
                    input_file = '{0}/perf_record_{1}.data'.format(utils.get_file_addr(PerfGlobals.directories, 'record'), cnt + 1)
                    utils.create_directory(directory)
                    for tid in critical_items[key]:
                        perf = PerfDiag(tid, directory)
                        perf.do_report(input_file)      
    else:
        exit()
        
def stat_util(critical_items):
    for key in critical_items:
        if key != 'counters':
            directory = '{0}/{1}'.format(utils.get_file_addr(PerfGlobals.directories, 'stat'), key)
            utils.create_directory(directory)
            for tid in critical_items[key]:
                perf = PerfDiag(tid, directory)
                perf.do_stat()
                
def latency_util():
    if PerfDiag.process_exiting_check('sched'):
        latency_analysis = {}
        for cnt in range(PerfGlobals.number_of_sched):
            sched_file = '{0}/perf_sched_{1}.data'.format(utils.get_file_addr(PerfGlobals.directories, 'sched'), cnt+1)
            latency_file = '{0}/perf_latency_{1}.txt'.format(utils.get_file_addr(PerfGlobals.directories, 'latency'), cnt+1)
            utils.rename_file('perf_sched_{0}.data'.format(cnt+1), sched_file)
            PerfDiag.do_perf_latency(sched_file, latency_file)
            analyse_latency_report(latency_file, latency_analysis)
        return latency_analysis
    else:
        exit()
        
def analyse_latency_report(input_file, latency_analysis):
    data = utils.read_file(input_file, 4, -4)
    fields = ['Switches', 'Runtime', 'Average delay', 'Maximum delay']
    data_dict = get_data_dict(data, fields)
    for key in PerfGlobals.latency_key:
        if not latency_analysis.has_key(key):
            latency_analysis[key] = []
        sorted_res = sort_latency_data(data_dict, key, fields)
        latency_analysis[key].append(utils.get_top_10(sorted_res))
          
def sort_latency_data(data_dict, key, fields):
    sorted_res = OrderedDict()
    for key, value in sorted(data_dict.items(), key = lambda item : item[1][key], reverse = True):
        sorted_res[key] = data_dict[key]
    return sorted_res
    
def get_data_dict(data, fields):
    data_dict = {}  
    for line in data:
        line = line.strip().split()
        data_dict[line[PerfGlobals.latency_field_index['Tid']]] = {}
        for field in fields:
            data_dict[line[PerfGlobals.latency_field_index['Tid']]][field] = float(line[PerfGlobals.latency_field_index[field]])
    return data_dict

def counter_based_critical_items():
    file_list = utils.list_files(CounterMonitor.temp_directory)
    
    critical_items = defaultdict()
    for file_ in file_list:
        counters = utils.load_data('{0}/{1}'.format(CounterMonitor.temp_directory, file_))
        # counters = CounterMonitor.poison_counters(counters)

        for TS in counters['counters']:
            for counter in TS[TS.items()[0][0]]['counter']:
                drop = TS[TS.items()[0][0]]['counter'][counter]
                if not critical_items.has_key(counter):
                    critical_items[counter] = []
                critical_items[counter].append(int(drop))

    sorted_res = OrderedDict()
    for key, value in sorted(critical_items.items(), key = lambda item : item[1][len(item[1]) - 1] - item[1][0], reverse =True):
        sorted_res[key] = value

    return utils.get_top_10(sorted_res)

def drop_based_critical_items():
    handoff = utils.load_data(utils.get_file_addr(Commands.files, "handoff")) 
    # handoff = Commands.poison_queue(handoff)

    critical_items = defaultdict(dict)

    for TS in handoff["handoff"]:
        ts = TS.items()[0][0]
        for queue in TS[ts]['handoffq']:
            critical_items[queue['tid']]['name'] = queue['name']        # TODO : has_key()
            if not critical_items[queue['tid']].has_key('drops') :
                critical_items[queue['tid']]['drops'] = []                
            critical_items[queue['tid']]['drops'].append(queue['drops'])

    sorted_res = OrderedDict()
    
    for key, value in sorted(critical_items.items(), key = lambda item : item[1]['drops'][len(critical_items[item[0]]['drops']) - 1] - item[1]['drops'][0], reverse = True):
        sorted_res[key] = value

    return utils.get_top_10(sorted_res)

def cpu_based_critical_items():
    data = utils.load_data(utils.get_file_addr(CpuMonitor.files, "all"))
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

    return utils.get_top_10(sorted_res)

def extract_critical_items(analysis_list, diag_list):
    critical_items = OrderedDict()
    for category in analysis_list:
        if category == 'cpu':
            critical_items['cpu'] = cpu_based_critical_items()
        elif category == 'handoff_drops':
            critical_items['drops'] = drop_based_critical_items()
        elif category == 'counters':
            critical_items['counters'] = counter_based_critical_items()
            
    tool = 'perf'
    if tool in diag_list:
        critical_items = do_perf_diag(critical_items)
            
    return critical_items