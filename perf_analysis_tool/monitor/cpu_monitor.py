import sys
sys.path.append('perf_analysis_tool')

import psutil
import threading
import time
from collections import OrderedDict

import utils
import global_variable
from monitor import monitor_utils

class CpuMonitor:    
    
    temp_directory = global_variable.temp_directory + 'cpu' 
    files = {
        "all" : "{0}/all.json".format(temp_directory)
    }
    
    if global_variable.threshold_detection_mode:
        cpu_threshold = {}
        
    def __init__(self, process):
        self.name = process['name']
        if process.has_key('trigger'):
            self.trigger = process['trigger']
        else:
            self.trigger = None
        self.file_addr = utils.get_file_addr(CpuMonitor.files, self.name, CpuMonitor.temp_directory, 'json')
        self.parsed_output = {}
        
    def __trigger_check(self, cpu_percent):
        if self.trigger:
            with global_variable.trigger_lock: 
                if global_variable.is_triggered == 0:
                    if monitor_utils.is_trigger_hits(cpu_percent, self.trigger):
                            print('triggered -> cpu')
                            monitor_utils.do_start_perf()
                        
    def __get_thread(self, proc, thread, bandwidth) :
        thread_entry = {}
        thread_entry['tid'] = thread.id
        try:
            t = psutil.Process(thread.id)
            thread_entry['name'] = t.name()
        except:
            return None
        try:
            thread_entry['cpu_percent'] = CpuMonitor.__get_cpu_percent(proc, thread)
        except:
            thread_entry['cpu_percent'] = 0.0    
        thread_entry['user_time'] = thread.user_time
        thread_entry['system_time'] = thread.system_time   
        
        if global_variable.threshold_detection_mode:
            if not CpuMonitor.cpu_threshold.has_key(thread_entry['tid']):
                CpuMonitor.cpu_threshold[thread_entry['tid']] = {}
                CpuMonitor.cpu_threshold[thread_entry['tid']]['value_based'] = []
                CpuMonitor.cpu_threshold[thread_entry['tid']]['bandwidth_based'] = []
            monitor_utils.update_threshold_list(CpuMonitor.cpu_threshold[thread_entry['tid']]['value_based'], 'value', thread_entry['cpu_percent'], bandwidth)               
            monitor_utils.update_threshold_list(CpuMonitor.cpu_threshold[thread_entry['tid']]['bandwidth_based'], 'bandwidth', thread_entry['cpu_percent'], bandwidth)   
                                        
        elif global_variable.auto_mode and global_variable.is_triggered == 0:
            self.__trigger_check(thread_entry['cpu_percent'])
                
        return thread_entry
    
    def __get_sample(self, proc, bandwidth) :
        sample = {}
        time_stamp = time.time()
        sample[time_stamp] = {}
        sample[time_stamp]['bandwidth'] = bandwidth
        sample[time_stamp]['cpu_percent'] = proc.cpu_percent(interval = 0.1)

        thread_objects = []
        for thread in proc.threads() :
            t = utils.CustomTimer(0, self.__get_thread, [proc, thread, bandwidth])
            t.start()
            thread_objects.append(t)
            
        for t in thread_objects:
            if t.join() != None:
                if not sample[time_stamp].has_key('threads'):
                    sample[time_stamp]['threads'] = []
                sample[time_stamp]['threads'].append(t.join())

        return sample

    def __get_details(self, proc) :
        process_entry = OrderedDict()
        try:
            process_entry['pid'] = proc.pid
            process_entry['name'] = proc.name()
            process_entry['samples'] = []
        except:
            pass
        return process_entry
                
    def __collect_sample(self, bandwidth) :
        if self.name == 'all' :
            for proc in psutil.process_iter():
                index = CpuMonitor.__find_index(self.parsed_output, proc)
                if(index == -1):
                    self.parsed_output[self.name].append(self.__get_details(proc))
                    index = len(self.parsed_output['all']) - 1
                self.parsed_output[self.name][index]['samples'].append(self.__get_sample(proc, bandwidth))
        else :
            proc = CpuMonitor.get_proc_object(self.name)
            if proc != None:
                if self.parsed_output[self.name].has_key('samples'):
                    self.parsed_output[self.name]['samples'].append(self.__get_sample(proc, bandwidth))
                            
    def get_cpu_profile(self):                    # making a room for process        
        if self.name == 'all' :
            self.parsed_output[self.name] = []
            for proc in psutil.process_iter():
                self.parsed_output[self.name].append(self.__get_details(proc))
        else :
            self.parsed_output[self.name] = {}
            proc = CpuMonitor.get_proc_object(self.name)
            if proc != None:
                self.parsed_output[self.name] = self.__get_details(proc)
        
        self.__call_repeatedly(self.__collect_sample)
        CpuMonitor.dump_output(self.parsed_output, self.file_addr)
        
    def __call_repeatedly(self, target_fun):
        thread_objects = []
        for sample_count in range(global_variable.no_of_sample):
            bandwidth = monitor_utils.get_bandwidth() 
            tObj = threading.Thread(target = target_fun, args = [bandwidth, ])
            tObj.start()
            thread_objects.append(tObj)
            time.sleep(global_variable.sample_frequency)
        
        for tObj in thread_objects:
            tObj.join()
            
    @staticmethod
    def __find_index(data, proc) :
        for index in range(len(data['all'])) :
            if proc.pid == data['all'][index]['pid'] :
                return index
        return -1
    
    @staticmethod
    def __get_cpu_percent(proc, t):
        total_percent = proc.cpu_percent(interval = 0.1)
        total_time = sum(proc.cpu_times())
        return total_percent * ((t.system_time + t.user_time)/total_time)
                
    @staticmethod
    def get_proc_object(name):
        try:
            for proc in psutil.process_iter():
                if proc.name() == name:
                    return proc
        except:
            return None
            
    @staticmethod
    def dump_output(parsed_output, file_addr):
        utils.create_directory(CpuMonitor.temp_directory)
        utils.write_file(parsed_output, file_addr)
    
