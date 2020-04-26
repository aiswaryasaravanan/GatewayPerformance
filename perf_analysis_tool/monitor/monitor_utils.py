import global_variable
from diag.perf.perf_diag import PerfDiag
from diag.perf.perf_globals import PerfGlobals    
import random
    
def is_trigger_hits(drop, trigger_value):
    if drop >= trigger_value:
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
    bandwidth = random.randint(90000, 200000)
    return bandwidth
