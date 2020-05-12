import sys
sys.path.append('perf_analysis_tool')

import os
import shutil
import json
import commands
from zipfile import ZipFile
from threading import _Timer
from prettytable import PrettyTable
import random
from collections import OrderedDict

import global_variable 
from diag.perf.perf_globals import PerfGlobals

def check_validity(arg_dict):
    if sum(map(bool, [arg_dict['zip_file'], arg_dict['auto_mode'], arg_dict['threshold_detection_mode']])) <= 1:
        if arg_dict['duration'] or arg_dict['output_threshold_file']:
            if arg_dict['threshold_detection_mode']:
                return True
            return False
        if arg_dict['window_size'] or arg_dict['consecutive_threshold_exceed_limit'] or arg_dict['mode'] or arg_dict['input_threshold_file']:
            if arg_dict['auto_mode']:
                return True
            return False
        return True
    else:
        return False
    
def set_default(arg_dict):
    if arg_dict['threshold_detection_mode'] and not arg_dict['duration']:
        arg_dict['duration'] = 50
        
    if arg_dict['threshold_detection_mode'] and not arg_dict['output_threshold_file']:
        arg_dict['output_threshold_file'] = global_variable.output_directory + '/threshold.json'
        if is_file_exists(arg_dict['output_threshold_file']):
            add_tag_old(arg_dict['output_threshold_file'])
        
    if arg_dict['auto_mode'] and not arg_dict['window_size']:
        arg_dict['window_size'] = 5
        
    if arg_dict['auto_mode'] and not arg_dict['consecutive_threshold_exceed_limit']:
        arg_dict['consecutive_threshold_exceed_limit'] = 2
        
    if arg_dict['auto_mode'] and not arg_dict['mode']:
        arg_dict['mode'] = 'value'
        
    if arg_dict['auto_mode'] and not arg_dict['input_threshold_file']:
        arg_dict['input_threshold_file'] = global_variable.output_directory + '/threshold.json'
        
def set_globals(arg_dict):
    
    global_variable.offline_mode = arg_dict['zip_file']
    
    global_variable.threshold_detection_mode = arg_dict['threshold_detection_mode']
    if arg_dict['threshold_detection_mode']:
        global_variable.duration = arg_dict['duration']
        global_variable.no_of_sample = get_no_of_sample(global_variable.sample_frequency, global_variable.duration)
        global_variable.threshold_dump_file = arg_dict['output_threshold_file']
    
    global_variable.auto_mode = arg_dict['auto_mode']
    if arg_dict['auto_mode']:
        global_variable.window_size = arg_dict['window_size']
        global_variable.consecutive_threshold_exceed_limit = arg_dict['consecutive_threshold_exceed_limit']
        global_variable.mode = arg_dict['mode']
        global_variable.threshold_dump_file = arg_dict['input_threshold_file']

class CustomTimer(_Timer):
    def __init__(self, interval, function, args=[], kwargs={}):
        self._original_function = function
        super(CustomTimer, self).__init__(interval, self._do_execute, args, kwargs)

    def _do_execute(self, *a, **kw):
        self.result = self._original_function(*a, **kw)

    def join(self):
        super(CustomTimer, self).join()
        return self.result

def create_directory(directory) :
    try :
        os.mkdir(directory)
    except :
        if os.path.exists(directory):                            # File exists
            pass
        else :                                                   # No such file or directory 
            directories = directory.split('/')                    
            directory_path = ''
            for d in directories :
                if d == '':
                    directory_path += '/'
                    pass
                directory_path += d
                create_directory(directory_path)
                directory_path += '/'

def clear_directory(directory):
    if os.path.exists(directory) :
        shutil.rmtree(directory)

def move_directory(source_directory, destination_directory):
    if not os.path.exists(destination_directory) :
        create_directory(destination_directory)    
    shutil.move(source_directory, destination_directory)
    
def get_zip_files(directory):
    available_zip = execute_command("find {0} -maxdepth 1 -name '*.zip'".format(directory))
    available_zip = (available_zip.split('\n'))
    available_zip.sort()
    return available_zip

def add_tag_old(file_):
    path_ = file_.split('/')
    path_.insert(len(path_) - 1, 'backup')
    dest_file_ = '/'.join(path_)
    rename_file(file_, dest_file_ + '.old')
    
def restore_existing_zip():
    create_directory(global_variable.output_directory + '/backup')
    available_zip = get_zip_files(global_variable.output_directory)
    for file_ in available_zip:
        if file_:
            add_tag_old(file_)
    
def rename_file(source, destination):
    # try:
    os.rename(source, destination)
    # except:
    #     shutil.rmtree(destination)
    #     os.rename(source, destination)
    
def load_data(file_addr):
    with open(file_addr, 'r') as r_obj:
        data = json.load(r_obj)
    return data

def write_file(output, file_addr):
    with open(file_addr, "w") as wObj:        
        json.dump(output, wObj, indent = 4, sort_keys = False)

def write_txt_file(output, file_addr) :
    with open(file_addr, "w") as wObj:        
        wObj.write(output)

def get_file_addr(file_list, file, *args):
    if not file_list.has_key(file):
        return generate_file_name(file.split(' ')[0], args[0], args[1])
        # file_list.setdefault(file, 'temp_result/{0}/{1}.txt'.format(directory, file.split(' ')[0]))
    return file_list[file]

def get_command_list(command_list, command):
    if command_list.has_key(command):
        return command_list[command]
    return command                         # for custom commands

def execute_command(command) :
    result = commands.getoutput(command)
    return result

def generate_file_name(name, directory, file_type) :
    file_name = directory + '/' + str(name) + '.' + file_type
    return file_name

def get_no_of_sample(sample_frequency, duration):
    no_of_sample = int(duration / sample_frequency) + 1
    return no_of_sample

def delete_temporary_files():
    clear_directory('temp_result')
    global_variable.is_triggered = False          # reset
    global_variable.trigger_lock = None
    
def is_file_exists(file_name):
    if os.path.exists(file_name):
        return 1
    return 0

def list_files(directory):
    return os.listdir(directory)

def modify_drop(drop) :
    drop = int(drop)
    drop += random.randint(1, 1000)
    return drop

def check_and_delete():
    available_zip = get_zip_files(global_variable.output_directory)
    if len(available_zip) >= global_variable.window_size:
        sts = execute_command('rm {0}'.format(available_zip[0]))

def zip_output(time_stamp):
    path = 'temp_result'

    check_and_delete()

    with ZipFile('/{0}/diag_dump_{1}.zip'.format(global_variable.output_directory, time_stamp),'w') as zip:
        for root, directories, files in os.walk(path):
            for file_name in files:
                filepath = os.path.join(root, file_name)
                zip.write(filepath)

def unzip_output(file_name):
    with ZipFile(file_name, "r") as zip:
        zip.extractall()
        
def get_top_10(data):
    top_10 = OrderedDict()
    count = 0
    for key in data.keys():
        if count < 10 :
            top_10[key] = data[key]
            count +=1
        else :
            break
    return top_10

def align_table(table_object, fields, alignment):
    for field in fields :
        table_object.align[field] = alignment
        
def read_file(file_addr, from_line, to_line):
    with open (file_addr, 'r') as obj:
        content = obj.readlines()[from_line: to_line]
        return content
        
def generate_summary_report(critical_items):
    print('\n\tSummary Report\n')
    for key in critical_items:
        if key == 'cpu' or key == 'drops' or key == 'counters' :
            count = 0 
            fields = []
            print(key)
            if key == 'cpu':
                fields = ['Thread Name', key]
                table = PrettyTable(fields)
                for tid in critical_items[key]:
                    if count > 3:
                        break
                    table.add_row([critical_items[key][tid]['name'], get_average(critical_items[key][tid]['value'])])
                    count += 1
            elif key == 'drops':
                fields = ['Handoff Queue Name', key]
                table = PrettyTable(fields)
                for tid in critical_items[key]:
                    if count > 3:
                        break
                    increase_rate = critical_items[key][tid]['value'][len(critical_items[key][tid]['value']) - 1] - critical_items[key][tid]['value'][0]
                    total_drops = critical_items[key][tid]['value'][len(critical_items[key][tid]['value']) - 1]
                    table.add_row([critical_items[key][tid]['name'], str(increase_rate) + '(' + str(total_drops) + ')'])
                    count += 1
            elif key == 'counters':
                fields = ['Counter Name', 'drops']
                table = PrettyTable(fields)
                for name in critical_items[key]:
                    if count > 3:
                        break
                    increase_rate = critical_items[key][name]['value'][len(critical_items[key][name]['value']) - 1] - critical_items[key][name]['value'][0]
                    total_drops = critical_items[key][name]['value'][len(critical_items[key][name]['value']) - 1]
                    table.add_row([name, str(increase_rate) + '(' + str(total_drops) + ')'])
                    count += 1
            align_table(table, fields, 'l')
            print(table)
            del table
            
def generate_detailed_report(critical_items):
    for key in critical_items:
        if key == 'cpu':
            fields = ['Thread Name', key, "perf Report", "Perf Stat"]
        elif key == 'drops':
            fields = ['Handoff Queue Name', key, "perf Report", "Perf Stat"]
        elif key == 'counters':
            fields = ['Counter Name', 'drops']

        table = PrettyTable(fields)
        align_table(table, fields, 'l')

        if key == 'cpu' or key == 'drops':
            for tid in critical_items[key]:
                report = []
                for cnt in range(PerfGlobals.number_of_record):
                    report.append('Report_{0}\n'.format(cnt + 1))
                    rep = ''
                    content = read_file(generate_file_name(str(tid), '{0}/report{1}/{2}'.format(get_file_addr(PerfGlobals.directories, 'report'), str(cnt + 1), key), 'txt'), 8, -4)
                    report.append(rep.join(content))
                report = ''.join(report)
                                
                stat = ''
                content = read_file(generate_file_name(str(tid), '{0}/{1}'.format(get_file_addr(PerfGlobals.directories, 'stat'), key), 'txt'), 3, -2)
                stat = stat.join(content)

                if key == "cpu":
                    table.add_row([critical_items[key][tid]['name'], get_average(critical_items[key][tid]['value']) , report, stat])
                elif key =="drops":
                    increase_rate = critical_items[key][tid]['value'][len(critical_items[key][tid]['value']) - 1] - critical_items[key][tid]['value'][0]
                    total_drops = critical_items[key][tid]['value'][len(critical_items[key][tid]['value']) - 1]
                    table.add_row([critical_items[key][tid]['name'], str(increase_rate) + '(' + str(total_drops) + ')', report, stat])
        elif key == 'counters':
            for name in critical_items[key]:
                increase_rate = critical_items[key][name]['value'][len(critical_items[key][name]['value']) - 1] - critical_items[key][name]['value'][0]
                total_drops = critical_items[key][name]['value'][len(critical_items[key][name]['value']) - 1]
                table.add_row([name, str(increase_rate) + '(' + str(total_drops) + ')'])
                
        print(table)
        del table
        
def generate_latency_report(latency_processed):
    # from monitor.cpu_monitor import CpuMonitor
    print('Perf latency report:')
    
    for key in latency_processed:
        print('Based on ' + key)
        table = PrettyTable()
        table.add_column('Task', ['Switches', 'Maximum delay', 'Runtime', 'Average delay'])
        for task in latency_processed[key]:
            if task.split(':')[0] == '':
                task_id = task.split(':')[1]
            else:
                task_id = task
                # task = CpuMonitor.get_process_name(int(tid.split(':')[1]))
            table.add_column(task_id, [get_average(latency_processed[key][task]['Switches']), get_average(latency_processed[key][task]['Maximum delay']), get_average(latency_processed[key][task]['Runtime']), get_average(latency_processed[key][task]['Average delay'])])
        print(table)
        del(table)
        
def get_average(l):
    avg = sum(l) / len(l)
    return avg



