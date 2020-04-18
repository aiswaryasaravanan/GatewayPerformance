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
        print('{0} -i {1} > {2}'.format(command, input_file, output_file))
        print(sts)
        
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

        
    

# def init(record, sched, stat, latency):
#     utils.create_directory(utils.get_file_addr(global_variable_perf.files, 'record'))
#     utils.create_directory(utils.get_file_addr(global_variable_perf.files, 'report'))
#     utils.create_directory(utils.get_file_addr(global_variable_perf.files, 'sched'))
#     utils.create_directory(utils.get_file_addr(global_variable_perf.files, 'latency'))
    
#     global_variable_perf.sleep_record = record['sleep']
#     global_variable_perf.frequency = record['frequency']
#     global_variable_perf.number_of_record = record['number_of_record']
#     global_variable_perf.delay_between_record = record['delay_between_record']
#     global_variable_perf.sleep_sched = sched['sleep']
#     global_variable_perf.number_of_sched = sched['number_of_sched']
#     global_variable_perf.delay_between_sched = sched['delay_between_sched']
#     global_variable_perf.sleep_stat = stat['sleep']
#     global_variable_perf.events = stat['events']
#     global_variable_perf.latency_key = latency
    
# def do_perf_record() :
#     FNULL = open(os.devnull, 'w')
#     for cnt in range(global_variable_perf.number_of_record):
#         sts = subprocess.Popen("{0} -F {1} -o perf_record_{2}.data -- sleep {3} &".format(utils.get_command_list(global_variable_perf.command_list, 'record'), global_variable_perf.frequency, cnt+1, global_variable_perf.sleep_record), shell = True, stdout = FNULL, stderr = subprocess.STDOUT)
#         time.sleep(global_variable_perf.delay_between_record)       # on pupose
   
# def do_stat(directory, tid):
#     file_name = utils.generate_file_name(str(tid), directory, 'txt')
#     c = utils.CustomTimer(0, utils.execute_command, ["{0} -e {1} -t {2} sleep {3}".format(utils.get_command_list(global_variable_perf.command_list, 'stat'), ','.join(global_variable_perf.events), tid, global_variable_perf.sleep_stat)])
#     c.start()
#     utils.write_txt_file(c.join(), file_name)

# def collect_perf_stat(critical_items) :
#     for key in critical_items:
#         if key != 'counters':
#             directory = '{0}/{1}'.format(utils.get_file_addr(global_variable_perf.files, 'stat'), key)
#             utils.create_directory(directory)
#             for tid in critical_items[key]:
#                 do_stat(directory, tid)
                
# def do_report(directory, input_file, tid):
#     file_name = utils.generate_file_name(str(tid), directory, 'txt')
#     res = utils.execute_command("{0} --tid={1} -i {2} > {3}".format(utils.get_command_list(global_variable_perf.command_list, 'report'), tid, input_file, file_name))
    
# def collect_perf_report(critical_items):    
#     wait = 0                    
#     while utils.execute_command("ps aux | grep 'perf record' | grep -v grep | awk '{print $2}'"):
#         if wait >= 15:
#             print('killing')
#             pids = []
#             pids = utils.execute_command("ps aux | grep 'perf record' | grep -v grep | awk '{print $2}'").split('\n')
#             for pid in pids:
#                 utils.execute_command('kill -9 {0}'.format(pid))
#             exit()
            
#         wait += 1
#         time.sleep(1)
#         print('waiting for perf record to complete...')
#         continue
    
#     for cnt in range(global_variable_perf.number_of_record):
#         os.rename('perf_record_{0}.data'.format(cnt+1), '{0}/perf_record_{1}.data'.format(utils.get_file_addr(global_variable_perf.files, 'record'), cnt+1))
    
#     for key in critical_items:
#         if key != 'counters':
#             for cnt in range(global_variable_perf.number_of_record):
#                 directory = '{0}/{1}'.format(utils.get_file_addr(global_variable_perf.files, 'report') + str(cnt + 1), key)
#                 input_file = '{0}/perf_record_{1}.data'.format(utils.get_file_addr(global_variable_perf.files, 'record'), cnt + 1)
#                 utils.create_directory(directory)
#                 for tid in critical_items[key]:
#                     do_report(directory, input_file, tid)
                             
# def do_perf_sched():
#     FNULL = open(os.devnull, 'w')
#     for cnt in range(global_variable_perf.number_of_sched):
#         sts = subprocess.Popen("{0} -o perf_sched_{1}.data sleep {2} &".format(utils.get_command_list(global_variable_perf.command_list, 'sched'), cnt+1, global_variable_perf.sleep_sched), shell = True, stdout = FNULL, stderr = subprocess.STDOUT)
#         time.sleep(global_variable_perf.delay_between_sched)       # on pupose
        
# def do_perf_latency(input_file, output_file):
#     sts = utils.execute_command('{0} -i {1} > {2}'.format(utils.get_command_list(global_variable_perf.command_list, 'latency'), input_file, output_file))

# def collect_perf_latency():   
#     wait = 0       
#     while utils.execute_command("ps aux | grep 'perf sched' | grep -v grep | awk '{print $2}'"):
#         if wait >= 15:
#             print('killing')
#             pids = []
#             pids = utils.execute_command("ps aux | grep 'perf sched' | grep -v grep | awk '{print $2}'").split('\n')
#             for pid in pids:
#                 utils.execute_command('kill -9 {0}'.format(pid))
#             exit()
            
#         wait += 1
#         time.sleep(1)
#         print('waiting for perf sched to complete...')
#         continue
    
#     latency_analysis = {}
#     for cnt in range(global_variable_perf.number_of_sched):
#         sched_file = '{0}/perf_sched_{1}.data'.format(utils.get_file_addr(global_variable_perf.files, 'sched'), cnt+1)
#         latency_file = '{0}/perf_latency_{1}.txt'.format(utils.get_file_addr(global_variable_perf.files, 'latency'), cnt+1)
#         os.rename('perf_sched_{0}.data'.format(cnt+1), sched_file)
#         do_perf_latency(sched_file, latency_file)
#         analyse_latency_report(latency_file, latency_analysis)
#     return latency_analysis
        
# def analyse_latency_report(input_file, latency_analysis):
#     data = utils.read_file(input_file, 4, -4)
#     fields = ['Switches', 'Runtime', 'Average delay', 'Maximum delay']
#     data_dict = get_data_dict(data, fields)
#     for key in global_variable_perf.latency_key:
#         if not latency_analysis.has_key(key):
#             latency_analysis[key] = []
#         sorted_res = sort_latency_data(data_dict, key, fields)
#         latency_analysis[key].append(utils.get_top_10(sorted_res))
          
# def sort_latency_data(data_dict, key, fields):
#     sorted_res = OrderedDict()
#     for key, value in sorted(data_dict.items(), key = lambda item : item[1][key], reverse = True):
#         sorted_res[key] = data_dict[key]
#     return sorted_res
    
# def get_data_dict(data, fields):
#     data_dict = {}  
#     for line in data:
#         line = line.strip().split()
#         data_dict[line[global_variable_perf.latency_field_index['Tid']]] = {}
#         for field in fields:
#             data_dict[line[global_variable_perf.latency_field_index['Tid']]][field] = float(line[global_variable_perf.latency_field_index[field]])
#     return data_dict
