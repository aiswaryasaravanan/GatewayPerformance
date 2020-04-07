import global_variable

temp_directory = global_variable.temp_directory + 'perf'
files = {
    "stat" : "{0}/stat".format(temp_directory),
    "report" : "{0}/report/report".format(temp_directory),
    "record" : "{0}/record".format(temp_directory),
    "sched" : "{0}/sched".format(temp_directory),
    "latency" : "{0}/latency".format(temp_directory)
}
command_list = {
    "stat" : "perf stat",
    "record" : "perf record -s -a --call-graph dwarf",
    "report" : "perf report --call-graph=none",
    "sched" : "perf sched record",
    "latency" : "perf sched latency"
}

sleep_record = 0
frequency = 0
number_of_record = 0
delay_between_record = 0
sleep_sched = 0
number_of_sched = 0
delay_between_sched = 0
sleep_stat = 0
events = []