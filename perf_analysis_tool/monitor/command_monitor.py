import sys
sys.path.append('perf_analysis_tool')

import time
from collections import OrderedDict

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
        threshold_dump_commands = {}
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
        self.parsed_output = []
                            
    def get_handoff(self, command, bandwidth) :
        command_output = utils.execute_command(command)   
        current_sample = OrderedDict()
        time_stamp = time.time()
        current_sample['time_stamp'] = time_stamp
        current_sample['bandwidth'] = bandwidth
        current_sample['handoffq'] = eval(command_output)['handoffq']
        self.parsed_output.append(current_sample)
            
        # poison queue
        # self.parsed_output = Commands.poison_queue(self.parsed_output)
        # current_sample = self.parsed_output[len(self.parsed_output) - 1]
            
        # if threshold detection mode
        if global_variable.threshold_detection_mode:
            for queue in current_sample['handoffq']:
                monitor_utils.find_threshold(Commands.threshold_dump_commands, queue['name'], queue['drops'], bandwidth)
            
        # if auto mode
        elif global_variable.auto_mode and global_variable.is_triggered == 0:
            with global_variable.trigger_lock:          # wait for lock acquisition
                for queue in current_sample['handoffq']:
                    if global_variable.is_triggered != 0:
                        break
                    monitor_utils.trigger_check(self.trigger, Commands.threshold_dump_commands, queue['name'], queue['drops'])
                        
        # return command_output
        
    def get_custom_commands(self, command, bandwidth):
        command_output = utils.execute_command(command)
        self.parsed_output.append('time_stamp : ' + str(time.time()))
        self.parsed_output.append('bandwidth : ' + str(bandwidth))
        self.parsed_output.append('output : ')
        self.parsed_output.append(command_output)
        
    def get_command_output(self):
        if self.name == 'handoff':
            target_fun = self.get_handoff
            self.file_type = 'json'
        else: 
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
        length = len(handoff)
        if length == 1:
            # entry = handoff[0]
            # for queue in range(len(entry['handoffq'])):
            #     entry['handoffq'][queue]['drops'] = utils.modify_drop(entry['handoffq'][queue]['drops'])
            for queue in handoff[0]['handoffq']:
                queue['drops'] = utils.modify_drop(queue['drops'])
        else:
            current_index = length - 1
            current_timestamp_entry = handoff[current_index]
            previous_timestamp_entry = handoff[current_index - 1]
            
            for queue in range(len(current_timestamp_entry['handoffq'])):
                current_timestamp_entry['handoffq'][queue]['drops'] = utils.modify_drop(previous_timestamp_entry['handoffq'][queue]['drops'])

     
        return handoff
                
    @staticmethod
    def dump_output(parsed_output, file_addr, file_type):
        utils.create_directory(Commands.temp_directory)
        if file_type == "json":
            utils.write_file(parsed_output, file_addr)
        else:
            result = '\n'.join(parsed_output)
            utils.write_txt_file(result, file_addr)
            
 