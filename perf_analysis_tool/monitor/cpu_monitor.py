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
        threshold_dump_cpu = {}
    elif global_variable.auto_mode:
        from monitor import threshold_dump
        if threshold_dump:
            threshold_dump_cpu = threshold_dump['cpu']
        
    def __init__(self, process):
        self.name = process['name']
        if process.has_key('trigger'):
            self.trigger = process['trigger']
        else:
            self.trigger = None
        self.file_addr = utils.get_file_addr(CpuMonitor.files, self.name, CpuMonitor.temp_directory, 'json')
        self.parsed_output = []
                   
    def _get_thread(self, proc, thread, bandwidth) :
        thread_entry = {}
        thread_entry['tid'] = thread.id
        thread_entry['name'] = CpuMonitor.get_process_name(thread_entry['tid'])
        thread_entry['cpu_percent'] = CpuMonitor._get_cpu_percent(proc, thread) 
        thread_entry['user_time'] = thread.user_time
        thread_entry['system_time'] = thread.system_time   
        
        if global_variable.threshold_detection_mode:
            monitor_utils.find_threshold(CpuMonitor.threshold_dump_cpu, thread_entry['tid'], thread_entry['cpu_percent'], bandwidth)
                           
        elif global_variable.auto_mode and global_variable.is_triggered == 0:
            with global_variable.trigger_lock:          # wait for lock acquisition
                monitor_utils.trigger_check(self.trigger, CpuMonitor.threshold_dump_cpu, thread_entry['tid'], thread_entry['cpu_percent'])
                
        return thread_entry
    
    def _get_sample(self, proc, bandwidth) :
        
        sample = {}
        sample['time_stamp'] = time.time()
        sample['bandwidth'] = bandwidth
        sample['cpu_percent'] = proc.cpu_percent(interval = 0.1)

        thread_objects = []
        for thread in proc.threads() :
            t = utils.CustomTimer(0, self._get_thread, [proc, thread, bandwidth])
            t.start()
            thread_objects.append(t)
            
        for t in thread_objects:
            if t.join() != None:
                if not sample.has_key('threads'):
                    sample['threads'] = []
                sample['threads'].append(t.join())

        return sample

    def _get_details(self, proc) :
        process_entry = OrderedDict()
        process_entry['pid'] = proc.pid
        process_entry['name'] = CpuMonitor.get_process_name(process_entry['pid'])
        process_entry['samples'] = []
        return process_entry
                
    def _collect_sample(self, bandwidth) :
        if self.name == 'all' :
            for proc in psutil.process_iter():
                index = CpuMonitor._find_index(self.parsed_output, proc)
                if(index == -1):
                    self.parsed_output.append(self._get_details(proc))
                    index = len(self.parsed_output) - 1
                self.parsed_output[index]['samples'].append(self._get_sample(proc, bandwidth))
        else :
            proc = CpuMonitor.get_proc_object(self.name)
            if proc != None:
                if self.parsed_output[0].has_key('samples'):
                    self.parsed_output[0]['samples'].append(self._get_sample(proc, bandwidth))
                            
    def get_cpu_profile(self):                    # making a room for process        
        if self.name == 'all' :
            for proc in psutil.process_iter():
                self.parsed_output.append(self._get_details(proc))
        else :
            proc = CpuMonitor.get_proc_object(self.name)
            if proc != None:
                self.parsed_output.append(self._get_details(proc))
                
        thread_objects = []
        for sample_count in range(global_variable.no_of_sample):
            bandwidth = monitor_utils.get_bandwidth() 
            tObj = threading.Thread(target = self._collect_sample, args = [bandwidth, ])
            tObj.start()
            thread_objects.append(tObj)
            time.sleep(global_variable.sample_frequency)
        
        for tObj in thread_objects:
            tObj.join()
        
        CpuMonitor.dump_output(self.parsed_output, self.file_addr)
        
    @staticmethod
    def get_process_name(pid):
        try:
            t = psutil.Process(int(pid))
            return t.name()
        except :
            return None   
            
    @staticmethod
    def _find_index(data, proc) :
        for index in range(len(data)) :
            if proc.pid == data[index]['pid'] :
                return index
        return -1
    
    @staticmethod
    def _get_cpu_percent(proc, t):
        try:
            total_percent = proc.cpu_percent(interval = 0.1)
            total_time = sum(proc.cpu_times())
            cpu_percent = total_percent * ((t.system_time + t.user_time)/total_time)
            return cpu_percent
        except:
            return 0.0
                    
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
    
