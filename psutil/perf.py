import utils
import os
import time
import subprocess
import global_variable

def do_perf_record() :
    utils.create_directory('temp_result/perf')
    FNULL = open(os.devnull, 'w')
    for cnt in range(global_variable.record_count):
        sts = subprocess.Popen("perf record -s -F 999 -a --call-graph dwarf -o perf{0}.data -- sleep 10 &".format(cnt+1), shell = True, stdout = FNULL, stderr = subprocess.STDOUT)
        time.sleep(5)       # on pupose
    # sts = subprocess.Popen("perf record -s -F 999 -a --call-graph dwarf -o perf2.data -- sleep 10 &", shell = True, stdout = FNULL, stderr = subprocess.STDOUT)
   
def do_stat(events, directory, tid):
    file_name = utils.generate_file_name(directory, str(tid))
    c = utils.CustomTimer(0, utils.execute_command, ["{0} -e {1} -t {2} sleep 0.01".format(utils.get_command_list('perf_stat'), ','.join(events), tid)])
    c.start()
    utils.write_txt_file(c.join(), file_name)

def collect_perf_stat(events, critical_items) :
    for key in critical_items:
        if key != 'counters':
            directory = '{0}/{1}'.format(utils.get_file_addr('perf_stat'), key)
            utils.create_directory(directory)
            for tid in critical_items[key]:
                do_stat(events, directory, tid)
                
def do_report(directory, input_file, tid):
    file_name = utils.generate_file_name(directory, str(tid))
    # res = executeCommand("perf report --tid={0} --stdio > {1}".format(tid, fileName))
    res = utils.execute_command("perf report --call-graph=none --tid={0} -i {1} > {2}".format(tid, input_file, file_name))
    
def fun(directory, input_file, key, critical_items):
    directory = '{0}/{1}'.format(directory, key)
    utils.create_directory(directory)
    for tid in critical_items[key]:
        do_report(directory, input_file, tid)
                

def collect_perf_report(critical_items):    
    wait = 0                    
    while utils.execute_command("ps aux | grep 'perf record' | grep -v grep | awk '{print $2}'"):
        if wait >= 15:
            print('killing')
            utils.execute_command('kill -9 {0}'.format(utils.execute_command("ps aux | grep 'perf record' | grep -v grep | awk '{print $2}'")))
            exit()
            
        wait += 1
        time.sleep(1)
        print('waiting for perf record to complete...')
        continue
    
    for cnt in range(global_variable.record_count):
        os.rename('perf{0}.data'.format(cnt+1), 'temp_result/perf/perf{0}.data'.format(cnt+1))
        # os.rename('perf2.data', 'tempResult/perf/perf2.data')
    
    for key in critical_items:
        if key != 'counters':
            for cnt in range(global_variable.record_count):
                fun(utils.get_file_addr('perf_report') + str(cnt + 1), 'temp_result/perf/perf{0}.data'.format(cnt + 1), key, critical_items)
                # fun(utils.getFileAddr('perf report2'), 'temp_result/perf/perf2.data', key, critical_items)
            