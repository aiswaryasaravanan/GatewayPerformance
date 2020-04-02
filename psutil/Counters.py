import utils
import time

import global_variable
import perf

class Counters:
    
    def __init__(self):
        pass
    
    def __get_dpdk_interface_names(self):
        dpdk_ports_dump = utils.execute_command('debug.py -v --dpdk_ports_dump')
        dpdk_ports_dump = eval(dpdk_ports_dump)
        dpdk_interface_names = []
        for dump in dpdk_ports_dump:
            dpdk_interface_names.append(dump['name'])
        return dpdk_interface_names

    def __get_counter_samples(self, counters, trigger_lock):
        dpdk_interface_names = self.__get_dpdk_interface_names()
        counters_list = {}
        for name in dpdk_interface_names:
            counters_list['dpdk_{0}_pstat_ierrors'.format(name)] = utils.execute_command('{0} dpdk_{1}_pstat_ierrors'.format(utils.get_command_list('counters'), name))
            counters_list['dpdk_{0}_pstat_oerrors'.format(name)] = utils.execute_command('{0} dpdk_{1}_pstat_oerrors'.format(utils.get_command_list('counters'), name))
            counters_list['dpdk_{0}_pstat_imissed'.format(name)] = utils.execute_command('{0} dpdk_{1}_pstat_imissed'.format(utils.get_command_list('counters'), name))

        for cntr in counters:
            c = utils.CustomTimer(0, utils.execute_command, ["{0} {1}".format(utils.get_command_list('counters'), cntr['name'])])        # actual
            c.start()
            counters_list[cntr['name']] = c.join()
            
        return counters_list

    def get_counters(self, counters, no_of_sample, sample_frequency, trigger_lock) :
        output = {}
        output["counters"] = []

        delay = 0
        while no_of_sample > 0 :
            no_of_sample -= 1
            sample = {}
            
            c = utils.CustomTimer(delay, self.__get_counter_samples, [counters, trigger_lock])
            c.start()

            sample[time.time()] = c.join()
            output['counters'].append(sample)
            delay = sample_frequency                        # for now
            
        file_addr = utils.get_file_addr("counters")
        utils.write_file(output, file_addr)
        
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

        # utils.writeFile(counters, utils.get_file_addr('counters'))
        return counters