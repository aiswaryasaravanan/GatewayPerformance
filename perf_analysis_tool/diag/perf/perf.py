import sys
sys.path.append('perf_analysis_tool')

import os
import time
import subprocess

import utils
from diag.perf import global_variable_perf 

def init(record, sched, stat):
    utils.create_directory(utils.get_file_addr(global_variable_perf.files, 'record'))
    utils.create_directory(utils.get_file_addr(global_variable_perf.files, 'report'))
    utils.create_directory(utils.get_file_addr(global_variable_perf.files, 'sched'))
    utils.create_directory(utils.get_file_addr(global_variable_perf.files, 'latency'))
    
    global_variable_perf.sleep_record = record['sleep']
    global_variable_perf.frequency = record['frequency']
    global_variable_perf.number_of_record = record['number_of_record']
    global_variable_perf.delay_between_record = record['delay_between_record']
    global_variable_perf.sleep_sched = sched['sleep']
    global_variable_perf.number_of_sched = sched['number_of_sched']
    global_variable_perf.delay_between_sched = sched['delay_between_sched']
    global_variable_perf.sleep_stat = stat['sleep']
    global_variable_perf.events = stat['events']
    
def do_perf_record() :
    FNULL = open(os.devnull, 'w')
    for cnt in range(global_variable_perf.number_of_record):
        sts = subprocess.Popen("{0} -F {1} -o perf_record_{2}.data -- sleep {3} &".format(utils.get_command_list(global_variable_perf.command_list, 'record'), global_variable_perf.frequency, cnt+1, global_variable_perf.sleep_record), shell = True, stdout = FNULL, stderr = subprocess.STDOUT)
        time.sleep(global_variable_perf.delay_between_record)       # on pupose
   
def do_stat(directory, tid):
    file_name = utils.generate_file_name(str(tid), directory, 'txt')
    c = utils.CustomTimer(0, utils.execute_command, ["{0} -e {1} -t {2} sleep {3}".format(utils.get_command_list(global_variable_perf.command_list, 'stat'), ','.join(global_variable_perf.events), tid, global_variable_perf.sleep_stat)])
    c.start()
    utils.write_txt_file(c.join(), file_name)

def collect_perf_stat(critical_items) :
    for key in critical_items:
        if key != 'counters':
            directory = '{0}/{1}'.format(utils.get_file_addr(global_variable_perf.files, 'stat'), key)
            utils.create_directory(directory)
            for tid in critical_items[key]:
                do_stat(directory, tid)
                
def do_report(directory, input_file, tid):
    file_name = utils.generate_file_name(str(tid), directory, 'txt')
    res = utils.execute_command("{0} --tid={1} -i {2} > {3}".format(utils.get_command_list(global_variable_perf.command_list, 'report'), tid, input_file, file_name))
    
def collect_perf_report(critical_items):    
    wait = 0                    
    while utils.execute_command("ps aux | grep 'perf record' | grep -v grep | awk '{print $2}'"):
        if wait >= 15:
            print('killing')
            pids = []
            pids = utils.execute_command("ps aux | grep 'perf record' | grep -v grep | awk '{print $2}'").split('\n')
            for pid in pids:
                utils.execute_command('kill -9 {0}'.format(pid))
            exit()
            
        wait += 1
        time.sleep(1)
        print('waiting for perf record to complete...')
        continue
    
    for cnt in range(global_variable_perf.number_of_record):
        os.rename('perf_record_{0}.data'.format(cnt+1), '{0}/perf_record_{1}.data'.format(utils.get_file_addr(global_variable_perf.files, 'record'), cnt+1))
    
    for key in critical_items:
        if key != 'counters':
            for cnt in range(global_variable_perf.number_of_record):
                directory = '{0}/{1}'.format(utils.get_file_addr(global_variable_perf.files, 'report') + str(cnt + 1), key)
                input_file = '{0}/perf_record_{1}.data'.format(utils.get_file_addr(global_variable_perf.files, 'record'), cnt + 1)
                utils.create_directory(directory)
                for tid in critical_items[key]:
                    do_report(directory, input_file, tid)
                             
def do_perf_sched():
    FNULL = open(os.devnull, 'w')
    for cnt in range(global_variable_perf.number_of_sched):
        sts = subprocess.Popen("{0} -o perf_sched_{1}.data sleep {2} &".format(utils.get_command_list(global_variable_perf.command_list, 'sched'), cnt+1, global_variable_perf.sleep_sched), shell = True, stdout = FNULL, stderr = subprocess.STDOUT)
        time.sleep(global_variable_perf.delay_between_sched)       # on pupose
        
def do_perf_latency(input_file, output_file):
    sts = utils.execute_command('{0} -i {1} > {2}'.format(utils.get_command_list(global_variable_perf.command_list, 'latency'), input_file, output_file))

def collect_perf_latency():   
    wait = 0       
    while utils.execute_command("ps aux | grep 'perf sched' | grep -v grep | awk '{print $2}'"):
        if wait >= 15:
            print('killing')
            pids = []
            pids = utils.execute_command("ps aux | grep 'perf sched' | grep -v grep | awk '{print $2}'").split('\n')
            for pid in pids:
                utils.execute_command('kill -9 {0}'.format(pid))
            exit()
            
        wait += 1
        time.sleep(1)
        print('waiting for perf sched to complete...')
        continue
        
    for cnt in range(global_variable_perf.number_of_sched):
        sched_file = '{0}/perf_sched_{1}.data'.format(utils.get_file_addr(global_variable_perf.files, 'sched'), cnt+1)
        latency_file = '{0}/perf_latency_{1}.txt'.format(utils.get_file_addr(global_variable_perf.files, 'latency'), cnt+1)
        os.rename('perf_sched_{0}.data'.format(cnt+1), sched_file)
        do_perf_latency(sched_file, latency_file)
          