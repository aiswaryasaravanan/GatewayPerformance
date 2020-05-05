import sys
sys.path.append('perf_analysis_tool')

import os
import time
import subprocess
from collections import OrderedDict

import utils
from diag.perf.perf_globals import PerfGlobals

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
        command = "{0} -e {1} -t {2} sleep {3}".format(cmd, events, self.tid, sleep)
        c = utils.CustomTimer(0, utils.execute_command, [command])
        c.start()
        utils.write_txt_file(c.join(), self.file_name)
        
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
        
    @staticmethod
    def dump_output(output, file_addr):
        utils.write_txt_file(output, file_name)

        
