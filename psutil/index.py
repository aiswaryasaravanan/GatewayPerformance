import argparse
import threading
from collections import defaultdict, OrderedDict
import subprocess
import time
import os

import CpuProfile
import Handoff
import Counters
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
    
def get_diag_dump(input, no_of_sample, target_function):
    trigger_lock = threading.Lock()
    for key in input.keys():
        if key == "cpu":
            utils.create_directory('temp_result/{0}'.format(key))
            t1 = threading.Thread(target = utils.get_target_function(target_function, key), args = (input['cpu'], no_of_sample, input['sample_frequency'], trigger_lock, ))
            t1.start()

        elif key == "commands":
            utils.create_directory('temp_result/{0}'.format(key))
            for cmd in input[key]:
                command_name = cmd['name']
                t2 = threading.Thread(target = utils.get_target_function(target_function, command_name), args = (utils.get_file_addr(command_name), cmd, no_of_sample, input['sample_frequency'], trigger_lock, ))
                t2.start()

        elif key == "counters" :
            t3 = threading.Thread(target = utils.get_target_function(target_function, key), args = (input['counters'], no_of_sample, input['sample_frequency'], trigger_lock, ))
            t3.start()

    t1.join()
    t2.join()
    t3.join()
            
def main():
    
    cpu = CpuProfile.CpuProfile()
    handoff = Handoff.Handoff()
    counter = Counters.Counters()
    
    target_function = {
        "cpu" : cpu.get_cpu_profile,
        "handoff" : handoff.get_handoff,
        "counters" : counter.get_counters,
    }
    
    input = utils.load_data("input.json")    
    utils.clear_directory('temp_result')
    utils.create_directory(input['output_directory'])
    
    global_variable.auto_mode = input.has_key('auto_mode')
    
    arg_dict = parse_command_line_arguments()

    if arg_dict.items()[0][1] != None:            # cmdline arg is there
        time_stamp = time.time()
        utils.unzip_output(arg_dict.items()[0][1], input['output_directory'])
        critical_items = critical_threads.extract_critical_items(input)
        perf.collect_perf_report(critical_items)
        perf.collect_perf_stat(input['perf_stat'], critical_items)
        utils.create_summary(critical_items)
        utils.print_table(critical_items)
        utils.delete_temporary_files()            
        pass

    else:
        consecutive_threshold_exceed_limit = 0
        while True:

            utils.create_directory('temp_result')
            time_stamp = time.time()

            no_of_sample = utils.get_no_of_sample(input['sample_frequency'], input['duration'])

            get_diag_dump(input, no_of_sample, target_function)
            manifest.create_manifest()

            critical_items = critical_threads.extract_critical_items(input)

            if not global_variable.auto_mode:
                perf.do_perf_record()

            perf.collect_perf_report(critical_items)
            perf.collect_perf_stat(input['perf_stat'], critical_items)

            utils.create_summary(critical_items)
            utils.print_table(critical_items)

            utils.zip_output(input['output_directory'], time_stamp)
            utils.delete_temporary_files()

            if not global_variable.auto_mode :
                break

            consecutive_threshold_exceed_limit += 1
            if consecutive_threshold_exceed_limit == input['auto_mode']['consecutive_threshold_exceed_limit'] :
                break
        

if __name__ == "__main__" :
    main()
