import sys
sys.path.append('perf_analysis_tool')

import time

import utils
import global_variable
from monitor import monitor_utils

class Commands():  
    temp_directory = global_variable.temp_directory + 'commands'   
    files = {
        "handoff" : "{0}/handoff.json".format(temp_directory)
    }
    
    command_list = {
        "handoff" : "debug.py -v --handoff "
    }
    
    if global_variable.threshold_detection_mode:
        command_threshold = {}
    elif global_variable.auto_mode:
        from monitor import threshold_dump
        if threshold_dump:
            threshold_dump_commands = threshold_dump['commands']
    
    def __init__(self, command):
        self.name = command['name']
        if command.has_key('trigger'):
            self.trigger = command['trigger']
        else:
            self.trigger = None
        self.file_addr = utils.get_file_addr(Commands.files, self.name, Commands.temp_directory, 'txt')
        self.parsed_output = {}
    
    def __trigger_check(self, handoff):
        
        with global_variable.trigger_lock:          # wait for lock acquisition
            for queue in handoff['handoffq']:
                if global_variable.is_triggered == 0:
                    if self.trigger:
                        trigger_value = self.trigger
                    elif Commands.threshold_dump_commands['handoffq'].has_key(queue['name']):
                        mode = global_variable.mode
                        trigger_value = monitor_utils.get_threshold(Commands.threshold_dump_commands['handoffq'][queue['name']], mode)
                        
                    if 'trigger_value' in locals():
                        if monitor_utils.is_trigger_hits(queue['drops'], trigger_value):
                            print('triggered -> commands')
                            print(queue['name'], queue['drops'], trigger_value)
                            monitor_utils.do_start_perf()
                        else: 
                            continue
                break
                
    def get_handoff(self, command, bandwidth) :
            command_output = utils.execute_command(command)   
            current_output = {}
            time_stamp = time.time()
            current_output[time_stamp] = {}
            current_output[time_stamp]['bandwidth'] = bandwidth
            current_output[time_stamp]['handoffq'] = eval(command_output)['handoffq']
            self.parsed_output[self.name].append(current_output)
            
            self.parsed_output = Commands.poison_queue(self.parsed_output)
            # take out current value
            command_output = self.parsed_output['handoff'][len(self.parsed_output['handoff']) - 1][time_stamp]
            # command_output = eval(command_output)
            
            if global_variable.threshold_detection_mode:
                if not Commands.command_threshold.has_key('handoffq'):
                    Commands.command_threshold['handoffq'] = {}
                    for queue in command_output['handoffq']:
                        # if not Commands.command_threshold.has_key(queue['name']):
                        Commands.command_threshold['handoffq'][queue['name']] = {}
                        Commands.command_threshold['handoffq'][queue['name']]['value_based'] = []
                        Commands.command_threshold['handoffq'][queue['name']]['bandwidth_based'] = []
                for queue in command_output['handoffq']:
                    monitor_utils.update_threshold_list(Commands.command_threshold['handoffq'][queue['name']]['value_based'], 'value', queue['drops'], bandwidth)               
                    monitor_utils.update_threshold_list(Commands.command_threshold['handoffq'][queue['name']]['bandwidth_based'], 'bandwidth', queue['drops'], bandwidth)   

            elif global_variable.auto_mode and global_variable.is_triggered == 0:
                self.__trigger_check(command_output)
                        
            return command_output
        
    def get_custom_commands(self, command, bandwidth):
        command_output = utils.execute_command(command)
        self.parsed_output.append(str(time.time()))
        self.parsed_output.append(str(bandwidth))
        self.parsed_output.append(command_output)
        
    def get_command_output(self):
        if self.name == 'handoff':
            self.parsed_output[self.name] = []
            target_fun = self.get_handoff
            self.file_type = 'json'
        else: 
            self.parsed_output = []
            target_fun = self.get_custom_commands
            self.file_type = 'text'
        
        thread_objects = []
        for sample_count in range(global_variable.no_of_sample):
            bandwidth = monitor_utils.get_bandwidth()
            command = utils.get_command_list(Commands.command_list, self.name)
            c = utils.CustomTimer(0, target_fun, [command, bandwidth])        
            c.start()
            thread_objects.append(c)
            time.sleep(global_variable.sample_frequency)
            
        for tObj in thread_objects:
            tObj.join()
            
        Commands.dump_output(self.parsed_output, self.file_addr, self.file_type)
            
    @staticmethod
    def poison_queue(handoff) :
        length = len(handoff['handoff'])
        if length == 1:
            entry = handoff['handoff'][0]
            TS = entry.items()[0][0]
            for queue in range(len(entry[TS]['handoffq'])):
                entry[TS]['handoffq'][queue]['drops'] = utils.modify_drop(entry[TS]['handoffq'][queue]['drops'])
            pass
        else:
            current_index = length - 1
            previous_timestamp_entry = handoff['handoff'][current_index - 1]
            pre_TS = previous_timestamp_entry.items()[0][0]
            current_timestamp_entry = handoff['handoff'][current_index]
            cur_TS = current_timestamp_entry.items()[0][0]
            for queue in range(len(current_timestamp_entry[cur_TS]['handoffq'])):
                current_timestamp_entry[cur_TS]['handoffq'][queue]['drops'] = utils.modify_drop(previous_timestamp_entry[pre_TS]['handoffq'][queue]['drops'])
     
        return handoff
                
    @staticmethod
    def dump_output(parsed_output, file_addr, file_type):
        utils.create_directory(Commands.temp_directory)
        if file_type == "json":
            utils.write_file(parsed_output, file_addr)
        else:
            result = '\n'.join(parsed_output)
            utils.write_txt_file(result, file_addr)
            
 