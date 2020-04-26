import sys
sys.path.append('perf_analysis_tool')

import argparse
import threading
from collections import defaultdict, OrderedDict
import subprocess
import time
import os

from monitor.counter_monitor import CounterMonitor 
from monitor.command_monitor import Commands 
from monitor.cpu_monitor import CpuMonitor 
from analysis import root_cause_analysis
from diag.perf.perf_globals import PerfGlobals
from diag.perf.perf_diag import PerfDiag
import utils as utils
import manifest 
import global_variable 

def parse_command_line_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-F", "--filename", help="output zip file", type = file)
    parser.add_argument("-T", "--threshold_detection", help="duration for threshold detection mode", type = int)
    args = parser.parse_args()
    return vars(args)

def get_diag_dump(monitor):
    global_variable.trigger_lock = threading.Lock()
    thread_list = []
    for key in monitor.keys():
        if key == "cpu":
            for process in monitor['cpu']:
                cpu = CpuMonitor(process)
                t1 = threading.Thread(target = cpu.get_cpu_profile)
                t1.start()
                thread_list.append(t1)
        elif key == "commands" :
            for command in monitor[key]:
                cmd = Commands(command)
                t2 = threading.Thread(target = cmd.get_command_output)
                t2.start()
                thread_list.append(t2)
        elif key == "counters" :
            for counter in monitor[key]:
                cntr = CounterMonitor(counter)
                t3 = threading.Thread(target = cntr.get_counters)                
                t3.start()
                thread_list.append(t3)
                
    for t in thread_list:
        t.join()      
        
def init_global_variable(input):
    global_variable.duration = input['duration']
    global_variable.sample_frequency = input['sample_frequency']
    global_variable.no_of_sample = utils.get_no_of_sample(global_variable.sample_frequency, global_variable.duration)
    global_variable.output_directory = input['output_directory']
    global_variable.auto_mode = input.has_key('auto_mode')
    if global_variable.auto_mode:
        global_variable.window_size = input['auto_mode']['window_size']
        global_variable.consecutive_threshold_exceed_limit = input['auto_mode']['consecutive_threshold_exceed_limit']
        global_variable.is_triggered = 0
        global_variable.trigger_lock = None
    else:
        global_variable.window_size = None
        global_variable.consecutive_threshold_exceed_limit = None
        global_variable.is_triggered = None
        global_variable.trigger_lock = None
        
def init(input):
    utils.clear_directory(global_variable.temp_directory)
    init_global_variable(input)
    for diag_key in input['diag']:
        if diag_key == 'perf':
            perf_list = input['diag']['perf']
            perf_global_singleton_obj = PerfGlobals(perf_list['record'], perf_list['sched'], perf_list['stat'], perf_list['latency'])
            
    utils.create_directory(global_variable.output_directory)

                    
def main():

    input = utils.load_data("input2.json")    

    init(input)
        
    arg_dict = parse_command_line_arguments()
    
    if any(value != None for value in arg_dict.values()):       # cmdline arg is there
        if arg_dict['filename']:                                # -F option given
            print("perform zip op")
            # time_stamp = time.time()
            # utils.unzip_output(arg_dict.items()[0][1], input['output_directory'])
            # critical_items = critical_threads.extract_critical_items(input)
            # # perf.collect_perf_report(critical_items)
            # # perf.collect_perf_stat(critical_items)
            # utils.create_summary(critical_items)
            # utils.print_table(critical_items)
            # utils.delete_temporary_files()    
        elif arg_dict['threshold_detection']:
            global_variable.threshold_detection_mode = True
            global_variable.no_of_sample = arg_dict['threshold_detection']   
            get_diag_dump(input['monitor']) 
            utils.delete_temporary_files()        

    else:
        consecutive_threshold_exceed_limit = 0
        while True:

            utils.create_directory(global_variable.temp_directory)
            time_stamp = time.time()
            
            if input.has_key('monitor'):
                get_diag_dump(input['monitor'])
                while global_variable.auto_mode and global_variable.is_triggered == 0:
                    print("inside auto mode waiting for istrigered to set... calculated diag dump")
                    manifest.create_manifest()
                    utils.zip_output(time_stamp)
                    utils.delete_temporary_files()
                    get_diag_dump(input['monitor'])
                    
                print("diagDump collected")
                    
                manifest.create_manifest()
                if input['analysis'] and input['diag']:
                    diag_list = [tool for tool in input['diag']]
                    critical_items = root_cause_analysis.extract_critical_items(input['analysis'], diag_list)
                    utils.create_summary(critical_items)
                    utils.print_table(critical_items)

                utils.zip_output(time_stamp)
                utils.delete_temporary_files()

            if not global_variable.auto_mode :
                break

            consecutive_threshold_exceed_limit += 1
            if consecutive_threshold_exceed_limit == global_variable.consecutive_threshold_exceed_limit :
                break
        

if __name__ == "__main__" :
    main()
