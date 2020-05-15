import sys
sys.path.append('perf_analysis_tool')

import argparse
import threading
import time

from analysis import root_cause_analysis
from diag.perf.perf_globals import PerfGlobals
from diag.perf.perf_diag import perform_diag
import utils as utils
import manifest 
import global_variable 

def parse_command_line_arguments():
    parser = argparse.ArgumentParser(description = 'Perf-analysis tool')
    parser.add_argument("-F", "--zip_file", help="output zip file", type = file)
    parser.add_argument('-T', "--threshold_detection_mode", help= "Runs in Threshold detection mode", action = "store_true")
    parser.add_argument('-o', '--output_threshold_file', help = 'custom output file for threshold_detection_mode')
    parser.add_argument("-d", '--duration', help = 'Total duration for threshold-detection-mode', type = int)
    parser.add_argument('-A', '--auto_mode', help = 'Runs in Auto-mode', action = 'store_true')
    parser.add_argument('-w', '--window_size', help = 'size of window to accomodate file', type = int)
    parser.add_argument('-l', '--consecutive_threshold_exceed_limit', help = 'stop when exceeds this limit', type = int)
    parser.add_argument('-m', '--mode', help = 'mode - bandwidth based / value based', choices = {"value", "bandwidth"})
    parser.add_argument('-i', '--input_threshold_file', help = 'custom input threshold file for auto_mode')
    
    args = parser.parse_args()
    return vars(args)

def get_diag_dump(monitor):
    thread_list = []
    for key in monitor.keys():
        if key == "cpu":
            from monitor.cpu_monitor import CpuMonitor 
            for process in monitor['cpu']:
                cpu = CpuMonitor(process)
                t1 = threading.Thread(target = cpu.get_cpu_profile)
                t1.start()
                thread_list.append(t1)
        elif key == "commands" :
            from monitor.command_monitor import Commands 
            for command in monitor[key]:
                cmd = Commands(command)
                t2 = threading.Thread(target = cmd.get_command_output)
                t2.start()
                thread_list.append(t2)
        elif key == "counters" :
            from monitor.counter_monitor import CounterMonitor 
            for counter in monitor[key]:
                cntr = CounterMonitor(counter)
                t3 = threading.Thread(target = cntr.get_counters)                
                t3.start()
                thread_list.append(t3)
                
    for t in thread_list:
        t.join()    
        
def generate_report(critical_items, latency_processed):
    utils.generate_summary_report(critical_items)
    utils.generate_detailed_report(critical_items)
    utils.generate_latency_report(latency_processed)
     
def init_global_variable(input):
    global_variable.duration = input['duration']
    global_variable.sample_frequency = input['sample_frequency']
    global_variable.no_of_sample = utils.get_no_of_sample(global_variable.sample_frequency, global_variable.duration)
    if input.has_key('output_directory'):
        global_variable.output_directory = input['output_directory']
    else:
        global_variable.output_directory = utils.get_current_working_directory() + '/output'
        
def init(input):
    init_global_variable(input)
    if input.has_key('diag'):
        for diag_key in input['diag']:
            if diag_key == 'perf':
                perf_list = input['diag']['perf']
                perf_global_singleton_obj = PerfGlobals(perf_list['record'], perf_list['sched'], perf_list['stat'], perf_list['latency'])
                
    utils.clear_directory(global_variable.temp_directory)
    # if utils.is_file_exists(global_variable.output_directory):
    #     utils.restore_existing_zip()
    # else:
    #     utils.create_directory(global_variable.output_directory)
    
                    
def main():

    input = utils.load_data("input.json")     
    init(input)    
    time_stamp = time.time()   
    arg_dict = parse_command_line_arguments()
            
    if utils.check_validity(arg_dict):
        utils.set_default(arg_dict)
                        
        if global_variable.offline_mode:                                
            utils.unzip_output(arg_dict['zip_file'])
            if input['analysis']:
                critical_items = root_cause_analysis.extract_critical_items(input['analysis'])
                if input['diag']:
                    if not utils.is_file_exists(PerfGlobals.temp_directory):        # zip -> not triggered
                        print('No trigger in this zip')
                        exit()
                    latency_processed = root_cause_analysis.extract_top_latency()
                    generate_report(critical_items, latency_processed)
            utils.directory_reset()           
                
        elif global_variable.threshold_detection_mode:
            global_variable.output_directory = global_variable.output_directory + '/threshold'
            utils.create_directory(global_variable.output_directory)
            
            get_diag_dump(input['monitor']) 
            utils.directory_reset()        
                
            threshold = {}
            from monitor.cpu_monitor import CpuMonitor 
            threshold['cpu'] = CpuMonitor.threshold_dump_cpu
            
            from monitor.command_monitor import Commands
            threshold['commands'] = Commands.threshold_dump_commands
            
            from monitor.counter_monitor import CounterMonitor
            threshold['counters'] = CounterMonitor.threshold_dump_counter
                
            utils.write_file(threshold, global_variable.threshold_dump_file)
            
        elif global_variable.auto_mode:
            global_variable.output_directory = global_variable.output_directory + '/results/' + str(int(time_stamp))
            utils.create_directory(global_variable.output_directory)
            
            consecutive_threshold_exceed_limit = 0
            while True:
                utils.create_directory(global_variable.temp_directory)
                time_stamp = time.time()
                
                global_variable.trigger_lock = threading.Lock()
                if input.has_key('monitor'):
                    get_diag_dump(input['monitor'])
                    while global_variable.is_triggered == 0:
                        manifest.create_manifest()
                        utils.zip_output(time_stamp)
                        utils.directory_reset()
                        global_variable.trigger_lock = threading.Lock()
                        get_diag_dump(input['monitor'])
                                            
                    manifest.create_manifest()
                    
                    if input['analysis']:
                        critical_items = root_cause_analysis.extract_critical_items(input['analysis'])
                        if input['diag']:
                            perform_diag(input['diag'], critical_items)
                            latency_processed = root_cause_analysis.extract_top_latency()
                            generate_report(critical_items, latency_processed)

                    utils.zip_output(time_stamp)
                    utils.directory_reset()

                consecutive_threshold_exceed_limit += 1
                if consecutive_threshold_exceed_limit == global_variable.consecutive_threshold_exceed_limit :
                    break
        else:   
            global_variable.output_directory = global_variable.output_directory + '/results/' + str(int(time_stamp))
            utils.create_directory(global_variable.output_directory)
            
            if input.has_key('monitor'):
                get_diag_dump(input['monitor'])                            
                manifest.create_manifest()
                    
                if input['analysis']:
                    critical_items = root_cause_analysis.extract_critical_items(input['analysis'])
                    if input['diag']:
                        perform_diag(input['diag'], critical_items)
                        latency_processed = root_cause_analysis.extract_top_latency()
                        generate_report(critical_items, latency_processed)
                    
                utils.zip_output(time_stamp)
                utils.directory_reset()        
    else:
        print("something went wrong")    

if __name__ == "__main__" :
    main()

