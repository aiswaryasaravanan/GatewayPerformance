import psutil
import threading
import utils
from collections import OrderedDict
import time
import global_variable
import perf

class CpuProfile:
    def __init__(self):
        pass
                    
    def __get_cpu_percent(self, proc, t):
        total_percent = proc.cpu_percent(interval = 0.1)
        total_time = sum(proc.cpu_times())
        return total_percent * ((t.system_time + t.user_time)/total_time)

    def __get_thread(self, proc, thread, process, trigger_lock) :

        thread_entry = {}
        thread_entry['tid'] = thread.id

        t = psutil.Process(thread.id)
        thread_entry['name'] = t.name()
        try:
            thread_entry['cpu_percent'] = self.__get_cpu_percent(proc, thread)
        except:
            thread_entry['cpu_percent'] = 0.0    
        thread_entry['user_time'] = thread.user_time
        thread_entry['system_time'] = thread.system_time   
        
        with trigger_lock: 
            if global_variable.auto_mode and global_variable.is_triggered == 0:
                if process.has_key('trigger'):
                    if thread_entry['cpu_percent'] >= process['trigger']:
                        perf.do_perf_record()
                        global_variable.is_triggered = 1
                
        return thread_entry
    

    def __get_process_samples(self, proc, process, trigger_lock) :
        sample = {}
        time_stamp = time.time()
        sample[time_stamp] = {}
        sample[time_stamp]['cpu_percent'] = proc.cpu_percent(interval = 0.1)
        # sample[time_stamp]['threads'] = []

        thread_objects = []
        for thread in proc.threads() :
            if not sample[time_stamp].has_key('thread'):
                sample[time_stamp]['threads'] = []
            t = utils.CustomTimer(0, self.__get_thread, [proc, thread, process, trigger_lock])
            t.start()
            thread_objects.append(t)
            
        for t in thread_objects:
            sample[time_stamp]['threads'].append(t.join())

        return sample

    def __get_process_details(self, proc) :
        process_entry = OrderedDict()

        try:
            process_entry['pid'] = proc.pid
            process_entry['name'] = proc.name()
            process_entry['samples'] = []
        except:
            pass
        return process_entry
    
    def __find_index(self, data, proc) :
        for index in range(len(data['all'])) :
            if proc.pid == data['all'][index]['pid'] :
                return index
        return -1

    def __collect_next_process_sample(self, cpu, cpu_sampling_lock, trigger_lock) :
        for process in cpu:
            process_name = process['name']
            file_addr = utils.get_file_addr(process_name)

            with cpu_sampling_lock:
                data = utils.load_data(file_addr)

                if process_name == 'all' :
                    for proc in psutil.process_iter():
                        index = self.__find_index(data, proc)
                        if(index == -1):
                            data[process_name].append(self.__get_process_details(proc))
                            index = len(data['all']) - 1
                        data[process_name][index]['samples'].append(self.__get_process_samples(proc, process, trigger_lock))
                else :
                    try:
                        pid = data[process_name]["pid"]
                        data[process_name]['samples'].append(self.__get_process_samples(psutil.Process(pid), process, trigger_lock))
                    except:
                        pass
                utils.write_file(data, file_addr)
                
    def get_cpu_profile(self, cpu, no_of_sample, sample_frequency, trigger_lock):                    # making a room for process
        cpu_sampling_lock = threading.Lock()
        
        for process in cpu:
            process_name = process['name']
            output = {}
            if process_name == 'all' :
                output[process_name] = []
                for proc in psutil.process_iter():
                    output[process_name].append(self.__get_process_details(proc))
            else :
                output[process_name] = {}
                for proc in psutil.process_iter():
                    if proc.name() == process_name:
                        output[process_name] = self.__get_process_details(proc)
                        break

            file_addr = utils.get_file_addr(process_name)
            utils.write_file(output, file_addr)

        thread_objects = []
        delay = 0
        while no_of_sample > 0 :
            tObj = threading.Timer(delay, self.__collect_next_process_sample, [cpu, cpu_sampling_lock, trigger_lock])
            tObj.start()
            thread_objects.append(tObj)
            delay += sample_frequency
            no_of_sample -= 1

        for tObj in thread_objects:
            tObj.join()
    
