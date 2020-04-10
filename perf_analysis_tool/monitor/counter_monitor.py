import sys
sys.path.append('perf_analysis_tool')

import time

import global_variable
from diag.perf import perf
import utils

class CounterMonitor:
    temp_directory = global_variable.temp_directory + 'counters' 
    files = {
        # "dpdk_counters" : "{0}/dpdk_counters.json".format(temp_directory)
        "counters" : '{0}/counter.json'.format(temp_directory)
    }
    command_list = {
        "counters" : "getcntr -c",
        "dpdk_interface" : "debug.py -v --dpdk_ports_dump"
    }
    
    def __init__(self, counter):
        self.name = counter['name']
        if counter.has_key('trigger'):
            self.trigger = counter['trigger']
        else:
            self.trigger = None
        self.parsed_output = {}
        self.file_addr = utils.get_file_addr(CounterMonitor.files, 'counters', CounterMonitor.temp_directory, 'json')
    
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
        self.auto_trigger_check(current_output)
        return current_output

    def __get_counter_samples(self):
        current_output = {}
        current_output[self.name] = utils.execute_command("{0} {1}".format(utils.get_command_list(CounterMonitor.command_list, 'counters'), self.name))   
        self.auto_trigger_check(current_output)    
        return current_output
    
    def auto_trigger_check(self, current_output):
        with global_variable.trigger_lock:
            if global_variable.auto_mode and global_variable.is_triggered == 0:
                if self.trigger:
                    for cntr in current_output:
                        if utils.modify_drop(int(current_output[cntr])) >= self.trigger:
                            print('triggered - > counter')
                            perf.do_perf_record()
                            perf.do_perf_sched()
                            global_variable.is_triggered = 1
    
    def get_counters(self) :
        self.parsed_output['counters'] = []
        
        if self.name == "dpdk_counters":
            target_fun = self.__get_dpdk_counter_samples
        else:
            target_fun = self.__get_counter_samples
            
        for sample_count in range(global_variable.no_of_sample): 
            time_stamp = time.time()           
            c = utils.CustomTimer(0, target_fun)
            c.start()
            current_sample = {}
            current_sample[time_stamp] = c.join()
            self.parsed_output['counters'].append(current_sample)
            time.sleep(global_variable.sample_frequency)
            
        CounterMonitor.dump_output(self.parsed_output, self.file_addr)
        
                    
    @staticmethod
    def poison_counters(counters) :
        flag = 1
        for TS in counters['counters']:
            if flag :
                pre = TS
                flag = 0
                continue

            for counter in TS[TS.items()[0][0]]:
                TS[TS.items()[0][0]][counter] = utils.modify_drop(int(pre[pre.items()[0][0]][counter]))
            pre = TS

        return counters
            
    @staticmethod
    def dump_output(parsed_output, file_addr):
        # if is_file_exists(file_addr):
        #     print('inside if')
        #     flag = 0
        #     file_output = load_data(file_addr)
        #     for TS_parsed_output in parsed_output['counters']:
        #         for TS_file_output in file_output['counters']:
        #             if TS_parsed_output.items()[0][0] == TS_file_output.items()[0][0]:
        #                 for cntr in TS_parsed_output[TS_parsed_output.items()[0][0]]:
        #                     TS_file_output[TS_file_output.items()[0][0]][cntr] = TS_parsed_output[TS_parsed_output.items()[0][0]][cntr]
        #                     flag = 1
        #                 break
        #         if flag == 0:
        #             TS_file_output[TS_parsed_output.items()[0][0]] = {}
        #             TS_file_output[TS_parsed_output.items()[0][0]] = TS_parsed_output[TS_parsed_output.items()[0][0]]
                    
        #     parsed_output = file_output
        # else:
        #     print("inside else")
        #     create_directory(CounterMonitor.temp_directory)
        # write_file(parsed_output, file_addr)
        utils.create_directory(CounterMonitor.temp_directory)
        utils.write_file(parsed_output, file_addr)
