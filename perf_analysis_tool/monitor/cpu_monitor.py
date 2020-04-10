import sys
sys.path.append('perf_analysis_tool')

import psutil
import threading
import time
from collections import OrderedDict

import utils
import global_variable
from diag.perf import perf

class CpuMonitor:    
    
    temp_directory = global_variable.temp_directory + 'cpu' 
    files = {
        "all" : "{0}/all.json".format(temp_directory)
    }
        
    def __init__(self, process):
        self.name = process['name']
        if process.has_key('trigger'):
            self.trigger = process['trigger']
        self.file_addr = utils.get_file_addr(CpuMonitor.files, self.name, CpuMonitor.temp_directory, 'json')
        self.parsed_output = {}
                    
    def __get_thread(self, proc, thread) :
        thread_entry = {}
        thread_entry['tid'] = thread.id
        try:
            t = psutil.Process(thread.id)
            thread_entry['name'] = t.name()
        except:
            return
        try:
            thread_entry['cpu_percent'] = CpuMonitor.__get_cpu_percent(proc, thread)
        except:
            thread_entry['cpu_percent'] = 0.0    
        thread_entry['user_time'] = thread.user_time
        thread_entry['system_time'] = thread.system_time   
        
        with global_variable.trigger_lock: 
            if global_variable.auto_mode and global_variable.is_triggered == 0:
                try:
                    if thread_entry['cpu_percent'] >= self.trigger:
                        print("triggered -> cpu")
                        perf.do_perf_record()
                        perf.do_perf_sched()
                        global_variable.is_triggered = 1
                except:
                    pass        # instance variable trigger not found
                
        return thread_entry
    
    def __get_sample(self, proc) :
        sample = {}
        time_stamp = time.time()
        sample[time_stamp] = {}
        sample[time_stamp]['cpu_percent'] = proc.cpu_percent(interval = 0.1)

        thread_objects = []
        for thread in proc.threads() :
            t = utils.CustomTimer(0, self.__get_thread, [proc, thread])
            t.start()
            thread_objects.append(t)
            
        for t in thread_objects:
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
                
    def __collect_sample(self) :
        if self.name == 'all' :
            for proc in psutil.process_iter():
                index = CpuMonitor.__find_index(self.parsed_output, proc)
                if(index == -1):
                    self.parsed_output[self.name].append(self.__get_details(proc))
                    index = len(self.parsed_output['all']) - 1
                self.parsed_output[self.name][index]['samples'].append(self.__get_sample(proc))
        else :
            try:
                proc = CpuMonitor.get_proc_object(self.name)
                self.parsed_output[self.name]['samples'].append(self.__get_sample(proc))
            except:
                pass
                            
    def get_cpu_profile(self):                    # making a room for process        
        if self.name == 'all' :
            self.parsed_output[self.name] = []
            for proc in psutil.process_iter():
                self.parsed_output[self.name].append(self.__get_details(proc))
        else :
            self.parsed_output[self.name] = {}
            proc = CpuMonitor.get_proc_object(self.name)
            self.parsed_output[self.name] = self.__get_details(proc)
        
        self.__call_repeatedly(self.__collect_sample)
        CpuMonitor.dump_output(self.parsed_output, self.file_addr)
        
    def __call_repeatedly(self, target_fun):
        thread_objects = []
        for sample_count in range(global_variable.no_of_sample):
            tObj = threading.Thread(target = target_fun)
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
        for proc in psutil.process_iter():
            if proc.name() == name:
                return proc
            
    @staticmethod
    def dump_output(parsed_output, file_addr):
        utils.create_directory(CpuMonitor.temp_directory)
        utils.write_file(parsed_output, file_addr)
    
