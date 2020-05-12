import sys
sys.path.append('perf_analysis_tool')

import os
import time
import subprocess

import utils
from diag.perf.perf_globals import PerfGlobals
import global_variable

class PerfDiag:
    
    # utils.create_directory(utils.get_file_addr(PerfGlobals.directories, 'record'))
    # utils.create_directory(utils.get_file_addr(PerfGlobals.directories, 'report'))
    # utils.create_directory(utils.get_file_addr(PerfGlobals.directories, 'sched'))
    # utils.create_directory(utils.get_file_addr(PerfGlobals.directories, 'latency'))
    
    def __init__(self, tid, directory):
        self.tid = tid
        self.directory = directory
        self.file_name = utils.generate_file_name(self.tid, self.directory, 'txt')
                
    def do_stat(self):
        cmd = utils.get_command_list(PerfGlobals.command_list, 'stat')
        events = ','.join(PerfGlobals.events)
        sleep = PerfGlobals.sleep_stat
        command = "{0} -e {1} -t {2} sleep {3} > {4}".format(cmd, events, self.tid, sleep, self.file_name)
        c = utils.CustomTimer(0, utils.execute_command, [command])
        c.start()
        PerfDiag.dump_output(c.join(), self.file_name)
        
    def do_report(self, input_file):
        cmd = utils.get_command_list(PerfGlobals.command_list, 'report')
        res = utils.execute_command("{0} --tid={1} -i {2} > {3}".format(cmd, self.tid, input_file, self.file_name))
        
    @staticmethod
    def do_perf_record(output_file) :
        utils.create_directory(utils.get_file_addr(PerfGlobals.directories, 'record'))
        FNULL = open(os.devnull, 'w')
        command = utils.get_command_list(PerfGlobals.command_list, 'record')
        freq = PerfGlobals.frequency
        sleep = PerfGlobals.sleep_record
        sts = subprocess.Popen("{0} -F {1} -o {2} -- sleep {3} &".format(command, freq, output_file, sleep), shell = True, stdout = FNULL, stderr = subprocess.STDOUT)
        
    @staticmethod
    def do_perf_sched(output_file):
        utils.create_directory(utils.get_file_addr(PerfGlobals.directories, 'sched'))
        FNULL = open(os.devnull, 'w')
        command = utils.get_command_list(PerfGlobals.command_list, 'sched')
        sleep = PerfGlobals.sleep_sched
        sts = subprocess.Popen("{0} -o {1} sleep {2} &".format(command, output_file, sleep), shell = True, stdout = FNULL, stderr = subprocess.STDOUT)
    
    @staticmethod    
    def do_perf_latency(input_file, output_file):
        utils.create_directory(utils.get_file_addr(PerfGlobals.directories, 'latency'))
        command = utils.get_command_list(PerfGlobals.command_list, 'latency')
        sts = utils.execute_command('{0} -i {1} > {2}'.format(command, input_file, output_file))
        
    @staticmethod
    def dump_output(output, file_name):
        utils.write_txt_file(output, file_name)

        
def perform_diag(diag_list, critical_items):
    for tool in diag_list:
        if tool == 'perf':
            do_perf_diag(critical_items)

def do_perf_diag(critical_items):
    if not global_variable.auto_mode:
        start_profile()
    report_util(critical_items)
    stat_util(critical_items)
    latency_util()

def start_profile():
    for count in range(PerfGlobals.number_of_record):
        output_file = 'perf_record_{0}.data'.format(count+1)
        PerfDiag.do_perf_record(output_file)
        time.sleep(PerfGlobals.delay_between_record)
    for count in range(PerfGlobals.number_of_sched):
        output_file = 'perf_sched_{0}.data'.format(count+1)
        PerfDiag.do_perf_sched(output_file)
        time.sleep(PerfGlobals.delay_between_record)
            
def report_util(critical_items):
    if process_exiting_check('record'):
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
    if process_exiting_check('sched'):
        for cnt in range(PerfGlobals.number_of_sched):
            sched_file = '{0}/perf_sched_{1}.data'.format(utils.get_file_addr(PerfGlobals.directories, 'sched'), cnt+1)
            latency_file = '{0}/perf_latency_{1}.txt'.format(utils.get_file_addr(PerfGlobals.directories, 'latency'), cnt+1)
            utils.rename_file('perf_sched_{0}.data'.format(cnt+1), sched_file)
            PerfDiag.do_perf_latency(sched_file, latency_file)  
    else:
        exit()
        
def process_exiting_check(process):
    wait = 0          
    command = utils.get_command_list(PerfGlobals.command_list, process + '_exiting_check')         
    while utils.execute_command(command):
        if wait >= 15:
            print('killing')
            pids = []
            pids = utils.execute_command(command).split('\n')
            for pid in pids:
                utils.execute_command('kill -9 {0}'.format(pid))
            return False
            
        wait += 1
        time.sleep(1)
        print('waiting for perf to complete...')
        continue
    return True

