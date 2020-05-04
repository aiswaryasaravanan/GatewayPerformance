import sys
sys.path.append('perf_analysis_tool')

import global_variable
from diag.perf.perf_diag import PerfDiag
from diag.perf.perf_globals import PerfGlobals    
import utils
    
def is_trigger_hits(drop, trigger_value):
    if float(drop) >= float(trigger_value):
        return True
    return False
    
def do_start_perf():
    for count in range(PerfGlobals.number_of_record):
        output_file = 'perf_record_{0}.data'.format(count+1)
        PerfDiag.do_perf_record(output_file)
        PerfGlobals.delay_between_record
            
    for count in range(PerfGlobals.number_of_sched):
        output_file = 'perf_sched_{0}.data'.format(count+1)
        PerfDiag.do_perf_sched(output_file)
        PerfGlobals.delay_between_record
            
    global_variable.is_triggered = 1
    
def get_bandwidth():
    output = utils.execute_command('debug.py -v --link')
    output = eval(output)
    for link in output:
        if link['vpnState'] == 'STABLE':
            return link['bpsOfBestPathTx']

def update_threshold_list(threshold_list, key, value, bandwidth):
    if key == 'value':
        if len(threshold_list) == 2:
            index = threshold_list.index(min(threshold_list, key = lambda entry : entry[key]))
            threshold_list.remove(threshold_list[index])
    elif key == 'bandwidth':
        if len(threshold_list) == 2:
            index = threshold_list.index(max(threshold_list, key = lambda entry : entry[key]))
            threshold_list.remove(threshold_list[index])
    entry = {}
    entry['value'] = value
    entry['bandwidth'] = bandwidth
    threshold_list.append(entry)
    
def get_threshold(threshold_dump, key):
    if key == 'value':
        return max(threshold_dump['value_based'], key = lambda entry : entry[key])['value']
    elif key == 'bandwidth':
        return min(threshold_dump['bandwidth_based'], key = lambda entry : entry[key])['value']
