import sys
sys.path.append('perf_analysis_tool')

import global_variable
from diag.perf.perf_diag import start_profile
import utils

def find_threshold(threshold_dump_dict, key, value, bandwidth):
    if not threshold_dump_dict.has_key(key):
        threshold_dump_dict[key] = {}
        threshold_dump_dict[key]['value_based'] = []
        threshold_dump_dict[key]['bandwidth_based'] = []
    update_threshold_list(threshold_dump_dict[key]['value_based'], 'value', value, bandwidth)
    update_threshold_list(threshold_dump_dict[key]['bandwidth_based'], 'bandwidth', value, bandwidth)
    
def trigger_check(inp_trigger, threshold_dump_dict, key, value):
    if inp_trigger:
        trigger_value = inp_trigger
    elif threshold_dump_dict.has_key(str(key)):
        mode = global_variable.mode
        trigger_value = get_threshold(threshold_dump_dict[str(key)], mode)
        
    if 'trigger_value' in locals():
        if is_trigger_hits(value, trigger_value):
            global_variable.is_triggered = 1
            print('triggered -> {0}'.format(key))
            start_profile()
    
def is_trigger_hits(drop, trigger_value):
    if float(trigger_value) and float(drop) > float(trigger_value):
        return True
    return False

def get_bandwidth():
    output = utils.execute_command('debug.py -v --link')
    output = eval(output)
    for link in output:
        if link['vpnState'] == 'STABLE':
            return link['bpsOfBestPathTx']

def update_threshold_list(threshold_list, key, value, bandwidth):
    if key == 'value':
        if len(threshold_list) == 10:
            index = threshold_list.index(min(threshold_list, key = lambda entry : entry[key]))
            threshold_list.remove(threshold_list[index])
    elif key == 'bandwidth':
        if len(threshold_list) == 10:
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
