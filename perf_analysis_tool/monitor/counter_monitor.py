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
        threshold_dump_counter = {}
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
        self.parsed_output = []
        self.file_addr = utils.get_file_addr(CounterMonitor.files, 'counters')
    
    def _get_dpdk_interface_names(self):
        dpdk_ports_dump = utils.execute_command(utils.get_command_list(CounterMonitor.command_list, 'dpdk_interface'))
        dpdk_ports_dump = eval(dpdk_ports_dump)
        dpdk_interface_names = []
        for dump in dpdk_ports_dump:
            dpdk_interface_names.append(dump['name'])
        return dpdk_interface_names

    def _get_dpdk_counter_samples(self):
        dpdk_interface_names = self._get_dpdk_interface_names()
        cntrs = ['pstat_ierrors', 'pstat_oerrors', 'pstat_imissed']
        
        cmd = utils.get_command_list(CounterMonitor.command_list, 'counters')
        current_output = []
        
        for name in dpdk_interface_names:
            for cntr in cntrs:
                blob = {}
                blob['name'] = 'dpdk_{0}_{1}'.format(name, cntr)
                blob['drops'] = utils.execute_command('{0} dpdk_{1}_{2}'.format(cmd, name, cntr))
                current_output.append(blob)       
        
        # blob = {}
        # for name in dpdk_interface_names:
        #     blob['dpdk_{0}_pstat_ierrors'.format(name)] = utils.execute_command('{0} dpdk_{1}_pstat_ierrors'.format(utils.get_command_list(CounterMonitor.command_list, 'counters'), name))
        #     blob['dpdk_{0}_pstat_oerrors'.format(name)] = utils.execute_command('{0} dpdk_{1}_pstat_oerrors'.format(utils.get_command_list(CounterMonitor.command_list, 'counters'), name))
        #     blob['dpdk_{0}_pstat_imissed'.format(name)] = utils.execute_command('{0} dpdk_{1}_pstat_imissed'.format(utils.get_command_list(CounterMonitor.command_list, 'counters'), name))
        # current_output.extend([{name, drop} for name, drop in blob.items()])
        return current_output

    def _get_counter_samples(self):
        current_output = []
        blob = {}
        blob['name'] = self.name
        blob['drops'] = utils.execute_command("{0} {1}".format(utils.get_command_list(CounterMonitor.command_list, 'counters'), self.name))   
        current_output.append(blob)
        return current_output
        
    def get_counters(self) :
        
        if self.name == "dpdk_counters" :
            target_fun = self._get_dpdk_counter_samples
        else:
            target_fun = self._get_counter_samples
            
        for sample_count in range(global_variable.no_of_sample): 
            c = utils.CustomTimer(0, target_fun)
            c.start()
            time_stamp = time.time()
            current_sample = {}           
            current_sample['time_stamp'] = time_stamp
            bandwidth = monitor_utils.get_bandwidth()
            current_sample['bandwidth'] = bandwidth
            current_sample['counters'] = c.join()
            self.parsed_output.append(current_sample)
            
            # poision counter
            self.parsed_output = CounterMonitor.poison_counters(self.parsed_output)
            current_sample = self.parsed_output[len(self.parsed_output) - 1]
            
            # if threshold detection mode
            if global_variable.threshold_detection_mode:
                for cntr in current_sample['counters']:
                    monitor_utils.find_threshold(CounterMonitor.threshold_dump_counter, cntr['name'], cntr['drops'], bandwidth)

            # if auto mode
            elif global_variable.auto_mode and global_variable.is_triggered == 0:
                with global_variable.trigger_lock:          # wait for lock acquisition
                    for cntr in current_sample['counters']:
                        if global_variable.is_triggered != 0:
                            break
                        monitor_utils.trigger_check(self.trigger, CounterMonitor.threshold_dump_counter, cntr['name'], cntr['drops'])
            
            time.sleep(global_variable.sample_frequency)
            
        CounterMonitor.dump_output(self.parsed_output, self.file_addr)
                      
    @staticmethod
    def poison_counters(counters) :
        length = len(counters)
        if length == 1:
            entry = counters[0]
            for cntr in entry['counters']:
                cntr['drops'] = utils.modify_drop(cntr['drops'])
        else:
            current_index = length - 1
            current_timestamp_entry = counters[current_index]
            previous_timestamp_entry = counters[current_index - 1]
            
            for cntr in range(len(current_timestamp_entry['counters'])):
                current_timestamp_entry['counters'][cntr]['drops'] = utils.modify_drop(previous_timestamp_entry['counters'][cntr]['drops'])

        return counters
            
    @staticmethod
    def dump_output(parsed_output, file_addr):
        
        if not utils.is_file_exists(file_addr):
            utils.create_directory(CounterMonitor.temp_directory)
        else:                        
            file_output = utils.load_data(file_addr)
            for parsed_entry in parsed_output:
                flag = 0
                for file_entry in file_output:
                    if parsed_entry['time_stamp'] == file_entry['time_stamp']:
                        for cntr in parsed_entry['counters']:
                            file_entry['counters'].append(cntr)
                        flag = 1
                        break
                if flag == 0:
                    file_output.append(parsed_entry)
                    
            parsed_output = file_output

        utils.write_file(parsed_output, file_addr)
