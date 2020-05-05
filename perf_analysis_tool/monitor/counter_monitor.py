import sys
sys.path.append('perf_analysis_tool')

import time

import global_variable
from monitor import monitor_utils
import utils

class CounterMonitor:
    temp_directory = global_variable.temp_directory + 'counters' 
    files = {
        "counters" : '{0}/counters.json'.format(temp_directory)
    }
    command_list = {
        "counters" : "getcntr -c",
        "dpdk_interface" : "debug.py -v --dpdk_ports_dump"
    }
    
    if global_variable.threshold_detection_mode:
        counter_threshold = {}
    elif global_variable.auto_mode:
        from monitor import threshold_dump
        if threshold_dump:
            threshold_dump_counter = threshold_dump['counters']
    
    def __init__(self, counter):
        self.name = counter['name']
        if counter.has_key('trigger'):
            self.trigger = counter['trigger']
        else:
            self.trigger = None
        self.parsed_output = {}
        self.file_addr = utils.get_file_addr(CounterMonitor.files, 'counters')
    
    def __get_dpdk_interface_names(self):
        dpdk_ports_dump = utils.execute_command(utils.get_command_list(CounterMonitor.command_list, 'dpdk_interface'))
        dpdk_ports_dump = eval(dpdk_ports_dump)
        dpdk_interface_names = []
        for dump in dpdk_ports_dump:
            dpdk_interface_names.append(dump['name'])
        return dpdk_interface_names

    def __get_dpdk_counter_samples(self):
        dpdk_interface_names = self.__get_dpdk_interface_names()
        current_output = {}
        for name in dpdk_interface_names:
            current_output['dpdk_{0}_pstat_ierrors'.format(name)] = utils.execute_command('{0} dpdk_{1}_pstat_ierrors'.format(utils.get_command_list(CounterMonitor.command_list, 'counters'), name))
            current_output['dpdk_{0}_pstat_oerrors'.format(name)] = utils.execute_command('{0} dpdk_{1}_pstat_oerrors'.format(utils.get_command_list(CounterMonitor.command_list, 'counters'), name))
            current_output['dpdk_{0}_pstat_imissed'.format(name)] = utils.execute_command('{0} dpdk_{1}_pstat_imissed'.format(utils.get_command_list(CounterMonitor.command_list, 'counters'), name))
        return current_output

    def __get_counter_samples(self):
        current_output = {}
        current_output[self.name] = utils.execute_command("{0} {1}".format(utils.get_command_list(CounterMonitor.command_list, 'counters'), self.name))   
        return current_output
        
    def get_counters(self) :
        self.parsed_output['counters'] = []
        
        if self.name == "dpdk_counters" :
            target_fun = self.__get_dpdk_counter_samples
        else:
            target_fun = self.__get_counter_samples
            
        for sample_count in range(global_variable.no_of_sample): 
            c = utils.CustomTimer(0, target_fun)
            c.start()
            current_sample = {}
            time_stamp = time.time()           
            current_sample[time_stamp] = {}
            bandwidth = monitor_utils.get_bandwidth()
            current_sample[time_stamp]['bandwidth'] = bandwidth
            current_sample[time_stamp]['counter'] = c.join()
            self.parsed_output['counters'].append(current_sample)
            
            self.parsed_output = CounterMonitor.poison_counters(self.parsed_output)
            current_sample = self.parsed_output['counters'][len(self.parsed_output['counters']) - 1]
            counters = current_sample[time_stamp]['counter']
            
            if global_variable.threshold_detection_mode:
                self.__find_threshold(counters, bandwidth)

            elif global_variable.auto_mode and global_variable.is_triggered == 0:
                self.__trigger_check(current_sample[time_stamp]['counter'])
            
            time.sleep(global_variable.sample_frequency)
            
        CounterMonitor.dump_output(self.parsed_output, self.file_addr)
        
    def __trigger_check(self, counter):
        with global_variable.trigger_lock:          # wait for lock acquisition
            for cntr in counter:
                if global_variable.is_triggered == 0:
                    if self.trigger:
                        trigger_value = self.trigger
                    elif CounterMonitor.threshold_dump_counter.has_key(cntr):
                        mode = global_variable.mode
                        trigger_value = monitor_utils.get_threshold(CounterMonitor.threshold_dump_counter[cntr], mode)
                        
                    if 'trigger_value' in locals():
                        if monitor_utils.is_trigger_hits(counter[cntr], trigger_value):
                            print('triggered -> counters')
                            monitor_utils.do_start_perf()
                        else: 
                            continue
                break
    
        
    def __find_threshold(counters, bandwidth):
        for cntr in counters:
            if not CounterMonitor.counter_threshold.has_key(cntr):
                CounterMonitor.counter_threshold[cntr] = {}
                CounterMonitor.counter_threshold[cntr]['value_based'] = []
                CounterMonitor.counter_threshold[cntr]['bandwidth_based'] = []
            monitor_utils.update_threshold_list(CounterMonitor.counter_threshold[cntr]['value_based'], 'value', counters[cntr], bandwidth)
            monitor_utils.update_threshold_list(CounterMonitor.counter_threshold[cntr]['bandwidth_based'], 'bandwidth', counters[cntr], bandwidth)
                    
    @staticmethod
    def poison_counters(counters) :
        length = len(counters['counters'])
        if length == 1:
            entry = counters['counters'][0]
            TS = entry.items()[0][0]
            for cntr in entry[TS]['counter']:
                entry[TS]['counter'][cntr] = utils.modify_drop(entry[TS]['counter'][cntr])
            pass
        else:
            current_index = length - 1
            previous_timestamp_entry = counters['counters'][current_index - 1]
            pre_TS = previous_timestamp_entry.items()[0][0]
            current_timestamp_entry = counters['counters'][current_index]
            cur_TS = current_timestamp_entry.items()[0][0]
            for counter in current_timestamp_entry[cur_TS]['counter']:
                current_timestamp_entry[cur_TS]['counter'][counter] = utils.modify_drop(previous_timestamp_entry[pre_TS]['counter'][counter])
     
        return counters
            
    @staticmethod
    def dump_output(parsed_output, file_addr):
        
        if not utils.is_file_exists(file_addr):
            utils.create_directory(CounterMonitor.temp_directory)
        else:
            file_output = utils.load_data(file_addr)
            for TS_parsed_output in parsed_output['counters']:
                flag = 0
                for TS_file_output in file_output['counters']:
                    if TS_parsed_output.items()[0][0] == TS_file_output.items()[0][0]:
                        for cntr in TS_parsed_output[TS_parsed_output.items()[0][0]]:
                            TS_file_output[TS_file_output.items()[0][0]][cntr] = TS_parsed_output[TS_parsed_output.items()[0][0]][cntr]
                        flag = 1
                        break
                if flag == 0:
                    file_output['counters'].append(TS_parsed_output)
                    
            parsed_output = file_output

        utils.write_file(parsed_output, file_addr)
