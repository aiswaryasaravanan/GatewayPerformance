import argparse
import threading
from collections import defaultdict, OrderedDict
import subprocess
import time
import os

import CpuProfile
import Counters
import Commands
import utils
import manifest
import critical_threads
import perf
import global_variable

def parse_command_line_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-F", "--filename", help="output zip file", type = file)
    args = parser.parse_args()
    return vars(args)

def get_diag_dump(monitor, meta_record):
    global_variable.trigger_lock = threading.Lock()
    thread_list = []
    for key in monitor.keys():
        if key == "cpu":
            for process in monitor['cpu']:
                cpu = CpuProfile.CpuProfile(process)
                t1 = threading.Thread(target = cpu.get_cpu_profile)
                t1.start()
                thread_list.append(t1)
        elif key == "commands" :
            for command in monitor[key]:
                cmd = Commands.Commands(command)
                t2 = threading.Thread(target = cmd.get_command_output)
                t2.start()
                thread_list.append(t2)
        elif key == "counters" :
            for counter in monitor[key]:
                cntr = Counters.Counters(counter)
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
        
def do_perf_diag(critical_items, perf):
    if not global_variable.auto_mode:
        perf.do_perf_record()
        perf.do_perf_sched()

    perf.collect_perf_report(critical_items)
    perf.collect_perf_stat(critical_items)
    perf.collect_perf_latency()
                    
def main():

    input = utils.load_data("input.json")    
    init_global_variable(input)
    
    utils.clear_directory(global_variable.temp_directory)
    utils.create_directory(global_variable.output_directory)
    
    arg_dict = parse_command_line_arguments()

    if arg_dict.items()[0][1] != None:            # cmdline arg is there
        # time_stamp = time.time()
        # utils.unzip_output(arg_dict.items()[0][1], input['output_directory'])
        # critical_items = critical_threads.extract_critical_items(input)
        # perf.collect_perf_report(critical_items)
        # perf.collect_perf_stat(input['diag']['perf']['stat'], critical_items)
        # utils.create_summary(critical_items)
        # utils.print_table(critical_items)
        # utils.delete_temporary_files()            
        pass

    else:
        consecutive_threshold_exceed_limit = 0
        while True:

            utils.create_directory(global_variable.temp_directory)
            time_stamp = time.time()

            get_diag_dump(input['monitor'])
            manifest.create_manifest()

            critical_items = critical_threads.extract_critical_items(input['analysis'])

            if input['diag']['perf']:
                do_perf_diag(critical_items, input['diag']['perf'])

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
