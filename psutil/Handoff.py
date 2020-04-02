import utils
import time
import random
import global_variable
import perf

class Handoff:
    def __init__(self):
        pass
    
    def get_handoff(self, file_addr, command, no_of_sample, sample_fequency, trigger_lock) :
        
        output = {}
        output['handoff'] = []

        delay = 0
        while no_of_sample > 0 :

            no_of_sample -= 1
            sample = {}
            c = utils.CustomTimer(delay, utils.execute_command, [utils.get_command_list(command['name'])])        
            c.start()
            time_stamp = time.time()
            entry = {}
            entry = c.join()
            sample[time_stamp] = eval(entry)
            output['handoff'].append(sample)
            delay = sample_fequency
            
            with trigger_lock:
                if global_variable.auto_mode and global_variable.is_triggered == 0:
                    output_poisoned = Handoff.poison_queue(output)

                    index = len(output_poisoned['handoff']) - 1
                    TS = output_poisoned['handoff'][index]
                    for queue in TS[TS.items()[0][0]]['handoffq']:
                        if queue['drops'] >= command['trigger']:
                            perf.do_perf_record()
                            global_variable.is_triggered = 1
                            break

        utils.write_file(output, file_addr)
        
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

        # utils.write_file(handoff, utils.get_file_addr('handoff'))
        return handoff
    

