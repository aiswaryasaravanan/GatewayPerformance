import time

import utils
import global_variable
import perf

class Commands():  
    temp_directory = global_variable.temp_directory + 'commands'   
    files = {
        "handoff" : "{0}/handoff.json".format(temp_directory)
    }
    
    command_list = {
        "handoff" : "debug.py -v --handoff "
    }
    
    def __init__(self, command):
        self.name = command['name']
        if command.has_key('trigger'):
            self.trigger = command['trigger']
        self.file_addr = utils.get_file_addr(Commands.files, self.name, Commands.temp_directory, 'txt')
        self.parsed_output = {}
                
    def get_handoff(self, command) :
            command_output = utils.execute_command(command)   
            current_output = {}
            current_output[time.time()] = eval(command_output)
            self.parsed_output[self.name].append(current_output)
            
            with global_variable.trigger_lock:
                if global_variable.auto_mode and global_variable.is_triggered == 0:
                    output_poisoned = Commands.poison_queue(self.parsed_output)

                    index = len(output_poisoned['handoff']) - 1
                    TS = output_poisoned['handoff'][index]
                    for queue in TS[TS.items()[0][0]]['handoffq']:
                        try:
                            if queue['drops'] >= self.trigger:
                                print('triggered -> commands')
                                perf.do_perf_record()
                                perf.do_perf_sched()
                                global_variable.is_triggered = 1
                                break
                        except:
                            pass                # instance variable trigger not found
                        
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
        
        flag = 1
        for ts in handoff["handoff"] :
            if flag :
                pre = ts
                flag = 0
                continue

            for queue in range(len(ts[ts.items()[0][0]]["handoffq"])) :
                ts[ts.items()[0][0]]["handoffq"][queue]["drops"] = utils.modify_drop(pre[pre.items()[0][0]]["handoffq"][queue]["drops"])
            pre = ts

        return handoff
                
    @staticmethod
    def dump_output(parsed_output, file_addr, file_type):
        utils.create_directory(Commands.temp_directory)
        if file_type == "json":
            utils.write_file(parsed_output, file_addr)
        else:
            result = '\n'.join(parsed_output)
            utils.write_txt_file(result, file_addr)
            
 