import sys
sys.path.append('perf_analysis_tool')

import os
import shutil
import json
import commands
from zipfile import ZipFile
from threading import _Timer
# from prettytable import PrettyTable
import random
import time
from collections import OrderedDict

import global_variable 
from diag.perf.perf_globals import PerfGlobals


def check_validity(arg_dict):
    if sum(map(bool, [arg_dict['zip_file'], arg_dict['auto_mode'], arg_dict['threshold_detection_mode']])) <= 1:
        if arg_dict['duration'] or arg_dict['output_threshold_file']:
            if arg_dict['threshold_detection_mode']:
                return True
            return False
        if arg_dict['auto_mode']:
            if arg_dict['input_threshold_file']:
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
    if arg_dict['zip_file']:
        global_variable.offline_mode = True
    
    if arg_dict['threshold_detection_mode']:
        global_variable.threshold_detection_mode = arg_dict['threshold_detection_mode']
        if arg_dict['duration']:
            global_variable.duration = arg_dict['duration']
        else:
            global_variable.duration = 60
        global_variable.no_of_sample = get_no_of_sample(global_variable.sample_frequency, global_variable.duration)
        
        if arg_dict['output_threshold_file']:
            global_variable.threshold_dump_file = arg_dict['output_threshold_file']
        else:
            time_stamp = time.time()
            global_variable.threshold_dump_file = global_variable.output_directory + '/threshold/threshold_' + str(int(time_stamp)) + '.json'
            
    if arg_dict['auto_mode']:
        global_variable.auto_mode = arg_dict['auto_mode']
        global_variable.threshold_dump_file = arg_dict['input_threshold_file']
        
        if arg_dict['window_size']:
            global_variable.window_size = arg_dict['window_size']
        else:
            global_variable.window_size = 5
            
        if arg_dict['consecutive_threshold_exceed_limit']:
            global_variable.consecutive_threshold_exceed_limit = arg_dict['consecutive_threshold_exceed_limit']
        else:
            global_variable.consecutive_threshold_exceed_limit = 3
            
        if arg_dict['mode']:
            global_variable.mode = arg_dict['mode']
        else:
            global_variable.mode = 'value'
            
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
    except Exception as e:
        if e.strerror == 'File exists':                                # File exists
            pass
        elif e.strerror == 'No such file or directory':                                                   # No such file or directory 
            directories = directory.split('/')                    
            directory_path = ''
            for d in directories :
                if d == '':
                    directory_path += '/'
                    continue
                directory_path += d
                create_directory(directory_path)
                directory_path += '/'
        else:
            raise Exception(e.strerror)

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

# def add_tag_old(file_):
#     path_ = file_.split('/')
#     path_.insert(len(path_) - 1, 'backup')
#     dest_file_ = '/'.join(path_)
#     rename_file(file_, dest_file_ + '.old')
    
# def restore_existing_zip():
#     create_directory(global_variable.output_directory + '/backup')
#     available_zip = get_zip_files(global_variable.output_directory)
#     for file_ in available_zip:
#         if file_:
#             add_tag_old(file_)
    
def rename_file(source, destination):                                            # todo: Handle exception
    # try:
    os.rename(source, destination)
    # except:
    #     shutil.rmtree(destination)
    #     os.rename(source, destination)
    
def get_current_working_directory():
    cwd = os.getcwd()
    return cwd
    
def load_data(file_addr):
    with open(file_addr) as r_obj:
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

def directory_reset():
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

def append_list_of_list(tab_list, list_):
    for ind in range(len(list_)):
        tab_list[ind].append(list_[ind])

def print_table(list_):
    cols = len(list_[0])
    
    col_width = []
    for i in range(cols):
        col_width.append(max(len(line) for row in list_ for line in str(row[i]).split('\n')))

    dash = ['-'] * (sum(col_width) + (4 * cols))
    print(''.join(dash))
    for row in list_:
        max_line = max(len(str(col).split('\n')) for col in row)
        
        for line in range(max_line):
            for col_index in range(cols):
                if line < len(str(row[col_index]).split('\n')):
                    value = str(row[col_index]).split('\n')[line]
                else: 
                    value = ' '
                print("{0:<{colW}}  |".format(value, colW=col_width[col_index])),
            print('')
        
        print(''.join(dash))
    
def generate_summary_report(critical_items):
    print('\n\tSummary Report\n')
    for key in critical_items:
        count = 0 
        fields = []
        print(key)
        if key == 'cpu':
            fields = ['Thread Name', key]
        elif key == 'drops':
            fields = ['Handoff Queue Name', key]
        elif key == 'counters':
            fields = ['Counter Name', 'drops']
            
        # table = PrettyTable(fields)                                                               # prettytable
        tab_list = []                                                                               # prettytable alternative(manual method) 
        tab_list.append(fields)                                                                     # prettytable alternative(manual method) 
        for tid in critical_items[key]:
            if count > 3:
                break
            if key == 'cpu':
                name = critical_items[key][tid]['name']
                value = get_average(critical_items[key][tid]['value'])
            elif key == 'drops':
                name = critical_items[key][tid]['name']
                total_drops = get_total_drops(critical_items[key][tid]['value'])
                avg_drops = total_drops / global_variable.no_of_sample
                value = str(total_drops) + '(' + str(avg_drops) + ')'
            elif key == 'counters':
                name = tid
                total_drops = get_total_drops(critical_items[key][tid]['value'])
                avg_drops = total_drops / global_variable.no_of_sample
                value = str(total_drops) + '(' + str(avg_drops) + ')'
            # table.add_row([name, value])                                                          # prettytable
            tab_list.append([name, value])                                                          # prettytable alternative(manual method)
            count += 1
        # align_table(table, fields, 'l')                                                           # prettytable
        # print(table)                                                                              # prettytable
        # del table                                                                                 # prettytable
        print_table(tab_list)                                                                       # prettytable alternative(manual method)
            
def generate_detailed_report(critical_items):
    for key in critical_items:
        if key == 'cpu':
            fields = ['Thread Name', key, "perf Report", "Perf Stat"]
        elif key == 'drops':
            fields = ['Handoff Queue Name', key, "perf Report", "Perf Stat"]
        elif key == 'counters':
            fields = ['Counter Name', 'drops']

        # table = PrettyTable(fields)                                                               # prettytable 
        # align_table(table, fields, 'l')                                                           # prettytable 
        tab_list = []                                                                               # prettytable alternative(manual method)
        tab_list.append(fields)                                                                     # prettytable alternative(manual method)    

        if key == 'cpu' or key == 'drops':
            for tid in critical_items[key]:
                # field 1
                name = critical_items[key][tid]['name']
                # field 2
                if key == "cpu":
                    value = get_average(critical_items[key][tid]['value'])
                elif key =="drops":
                    total_drops = get_total_drops(critical_items[key][tid]['value']) 
                    avg_drops = total_drops / global_variable.no_of_sample
                    value = str(total_drops) + '(' + str(avg_drops) + ')'
                # field 3
                report = []
                for cnt in range(PerfGlobals.number_of_record):
                    report.append('Report_{0}\n'.format(cnt + 1))
                    content = read_file(generate_file_name(str(tid), '{0}/report{1}/{2}'.format(get_file_addr(PerfGlobals.directories, 'report'), str(cnt + 1), key), 'txt'), 8, -4)
                    report.append(''.join(content))
                report = ''.join(report)
                # field 4                
                stat = ''
                content = read_file(generate_file_name(str(tid), '{0}/{1}'.format(get_file_addr(PerfGlobals.directories, 'stat'), key), 'txt'), 3, -2)
                stat = ''.join(content)

                # table.add_row([name, value, report, stat])                                        # prettytable 
                tab_list.append([name, value, report, stat])                                        # prettytable alternative(manual method)
        elif key == 'counters':
            for name in critical_items[key]:
                total_drops = get_total_drops(critical_items[key][name]['value']) 
                avg_drops = total_drops / global_variable.no_of_sample
                value = str(total_drops) + '(' + str(avg_drops) + ')'
                
                # table.add_row([name, value])                                                      # prettytable 
                tab_list.append([name, value])                                                      # prettytable alternative(manual method)
                
        # print(table)                                                                              # prettytable 
        # del table                                                                                 # prettytable 
        print_table(tab_list)                                                                       # prettytable alternative(manual method)
        
def generate_latency_report(latency_processed):
    print('Perf latency report:')
    
    for key in latency_processed:
        print('Based on ' + key)
        # table = PrettyTable()                                                                     # prettytable
        # table.add_column('Task', ['Switches', 'Maximum delay', 'Runtime', 'Average delay'])       # prettytable
        fields = ['Task', 'Switches', 'Maximum delay', 'Runtime', 'Average delay']                  # prettytable alternative(manual method)
        tab_list = [[] for i in range(len(fields))]                                                 # prettytable alternative(manual method)
        append_list_of_list(tab_list, ['Task' ,'Switches', 'Maximum delay', 'Runtime', 'Average delay']) # prettytable alternative(manual method)
        for task in latency_processed[key]:
            if task.split(':')[0] != '':
                name = task.split(':')[0]
            else:
                name = task.split(':')[1]
            # prettytable
            # table.add_column(name, [get_average(latency_processed[key][task]['Switches']), get_average(latency_processed[key][task]['Maximum delay']), get_average(latency_processed[key][task]['Runtime']), get_average(latency_processed[key][task]['Average delay'])])
            # prettytable alternative(manual method)
            append_list_of_list(tab_list, [name, get_average(latency_processed[key][task]['Switches']), get_average(latency_processed[key][task]['Maximum delay']), get_average(latency_processed[key][task]['Runtime']), get_average(latency_processed[key][task]['Average delay'])])
        # print(table)                                                                                # prettytable
        # del(table)                                                                                  # prettytable
        print_table(tab_list)                                                                         # prettytable alternative(manual method)  
        
def get_average(list_):
    avg = sum(list_) / len(list_)
    return avg

def get_total_drops(list_):
    total_drops = int(list_[len(list_) - 1]) - int(list_[0])
    return total_drops




