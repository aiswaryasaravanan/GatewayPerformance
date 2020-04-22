import sys
sys.path.append('perf_analysis_tool')

import time

import utils
import global_variable
from diag.perf.perf_diag import PerfDiag
from diag.perf.perf_globals import PerfGlobals


class Commands():  
    temp_directory = global_variable.temp_directory + 'commands'   
    files = {
        "handoff" : "{0}/handoff.json".format(temp_directory)
    }
    
    command_list = {
        "handoff" : "debug.py -v --handoff "
    }
    
    if global_variable.trigger_calculation_mode:
        command_trigger = {}
    
    def __init__(self, command):
        self.name = command['name']
        if command.has_key('trigger'):
            self.trigger = command['trigger']
        else:
            self.trigger = None
        self.file_addr = utils.get_file_addr(Commands.files, self.name, Commands.temp_directory, 'txt')
        self.parsed_output = {}
        
    def __auto_trigger_check(self, handoff_drop, trigger_value):
        with global_variable.trigger_lock:
            if global_variable.is_triggered == 0:
                # output_poisoned = Commands.poison_queue(self.parsed_output)

                # index = len(self.parsed_output['handoff']) - 1
                # TS = self.parsed_output['handoff'][index]
                # for queue in TS[TS.items()[0][0]]['handoffq']:
                #     try:
                        # if queue['drops'] >= trigger_value:
                if handoff_drop >= trigger_value:
                    print('triggered -> commands')
                    for count in range(PerfGlobals.number_of_record):
                        output_file = 'perf_record_{0}.data'.format(count+1)
                        PerfDiag.do_perf_record(output_file)
                    for count in range(PerfGlobals.number_of_sched):
                        output_file = 'perf_sched_{0}.data'.format(count+1)
                        PerfDiag.do_perf_sched(output_file)
                    global_variable.is_triggered = 1
                    # except:
                    #     pass                # instance variable trigger not found
                
    def get_handoff(self, command) :
        time_stamp = time.time()
        command_output = utils.execute_command(command)   
        current_output = {}
        current_output[time_stamp] = eval(command_output)
        self.parsed_output[self.name].append(current_output)
            
        self.parsed_output = Commands.poison_queue(self.parsed_output)
        # take current output
        current_output = self.parsed_output['handoff'][len(self.parsed_output['handoff']) - 1][time_stamp]
            
        if global_variable.auto_mode and global_variable.trigger_calculation_mode:
            for queue in current_output['handoffq']:
                Commands.command_trigger = utils.update_trigger_blob(Commands.command_trigger, queue['name'], queue['drops'])
            
        if global_variable.auto_mode and not global_variable.trigger_calculation_mode:
            if hasattr(Commands, 'command_trigger'):
                for queue in current_output['handoffq']:
                    trigger_value = Commands.command_trigger[queue['name']]
                    self.__auto_trigger_check(queue['drops'], trigger_value)
            elif self.trigger:
                trigger_value = self.trigger
                for queue in current_output['handoffq']:
                    self.__auto_trigger_check(queue['drops'], trigger_value)
                    
            # if global_variable.trigger_mode and global_variable.is_trigger_calculated:
            #     for queue in current_output['handoffq']:
            #         trigger_value = Commands.command_trigger[queue['name']]
            #         auto_trigger_check(queue['drops'], trigger_value)
            # elif self.trigger and not global_variable.trigger_mode:
            #     trigger_value = self.trigger
            #     for queue in current_output['handoffq']:
            #         auto_trigger_check(queue['drops'], trigger_value)
                        
        return command_output
        
    def get_custom_commands(self, command):
        command_output = utils.execute_command(command)
        self.parsed_output.append(str(time.time()))
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
            c = utils.CustomTimer(0, target_fun, [utils.get_command_list(Commands.command_list, self.name)])        
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
            
 