import sys
sys.path.append('perf_analysis_tool')

import global_variable

# singleton class
class PerfGlobals:
    
    __instance = None
    
    temp_directory = global_variable.temp_directory + 'perf' 
        
    directories = {
        "stat" : "{0}/stat".format(temp_directory),
        "report" : "{0}/report".format(temp_directory),
        "record" : "{0}/record".format(temp_directory),
        "sched" : "{0}/sched".format(temp_directory),
        "latency" : "{0}/latency".format(temp_directory)
    }
    command_list = {
        "stat" : "perf stat",
        "record" : "perf record -s -a --call-graph dwarf",
        "report" : "perf report --call-graph=none",
        "sched" : "perf sched record",
        "latency" : "perf sched latency",
        "record_exiting_check" : "ps aux | grep 'perf record' | grep -v grep | awk '{print $2}'", 
        "sched_exiting_check" : "ps aux | grep 'perf sched' | grep -v grep | awk '{print $2}'"
    }
    latency_field_index = {
        "Tid" : 0,
        "Runtime" : 2,
        "Switches" : 5,
        "Average delay" : 8,
        "Maximum delay" : 12
    }
    
    sleep_record = 0
    frequency = 0
    number_of_record = 0
    delay_between_record = 0
    sleep_sched = 0
    number_of_sched = 0
    delay_between_sched = 0
    sleep_stat = 0
    events = []
    latency_key = ''
            
    def __init__(self, record, sched, stat, latency):
        if PerfGlobals.__instance == None:
            
            PerfGlobals.__instance = self
            
            PerfGlobals.sleep_record = record['sleep']
            PerfGlobals.frequency = record['frequency']
            PerfGlobals.number_of_record = record['number_of_record']
            PerfGlobals.delay_between_record = record['delay_between_record']
            PerfGlobals.sleep_sched = sched['sleep']
            PerfGlobals.number_of_sched = sched['number_of_sched']
            PerfGlobals.delay_between_sched = sched['delay_between_sched']
            PerfGlobals.sleep_stat = stat['sleep']
            PerfGlobals.events = stat['events']
            PerfGlobals.latency_key = latency
            
        else:
            raise Exception("This class is a singleton!")