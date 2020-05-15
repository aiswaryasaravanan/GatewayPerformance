## Perf-Analysis Tool

### Why this tool:
   This `Perf-Analysis tool` will identify the potential root cause of the performance issue in the production edge and generate the report. This `Perf-Analysis tool` makes use of `perf` tool which is a linux profiler tool.
   
### Input:

The input to this `Perf-Analysis tool` is a json file that contains the following,
   
- Total Duration and sample frequency interval
- Output directory
- List of processes, commands and counters to monitor
- List of what to analyse
- Diag tool(here perf) and its meta data

### How it works:

1. This tool will monitor the edge and collect,
    - CPU utilization percentage of all the active process and its threads using `psutil` library of python.
    - Counter drops using the proprietary command `getcntr -c <counter_name>`. For dpdk_counters, `debug.py --dpdk_ports_dump` will give the list of dpdk enabled ports.
    - Handoff queue drops using the proprietary command `debug.py --handoff`.
2. In addition, this will also execute the inputted custom commands if any.
3. These parsed data are dumped to a JSON file.
4. Then, the device is profiled using the following `perf` commands, and the results of which will be stored in a binary file for later analysis
    - `perf record` for collecting the profililing data,
    - `perf sched record` for collecting per task scheduling latency.
5. Meanwhile, the top processor consuming threads, and the threads with maximum drops have been identified (from the parsed JSON).
6. Now the following analysis is done for these top threads,
    - The profile data analysis using `perf report`, 
    - `perf sched latency` for summarizing scheduler latencies by task, including average and maximum delay, 
    - Performance counter statistics using `perf stat`.  
7. The results of these analysis forms the potential root cause report.

#### Various modes:

1. Offline mode:

    - This mode accepts the monitored zip file as a command line argument and thus allows offline processing. The inputted zip will havemonitored data (CPU stats, counters and handoff queue drops) and the perf profiled data.
    - From the inputted file, the top processor consuming threads, and the threads with maximum drops have been identified.
    - Having the perf binary file, the perf analysis will be done and the potential root cause report will be generated.


2. Threshold detection mode:

    - This mode will monitor the CPU utilization, counters and handoff queue drops for the given duration, and maintain the list of top x trigger value for every process, queues and counters.
    - Meanwhile, the trigger values for top x bandwidth were also maintained for every process, queues and counters.
    - Running the tool with `threshold_detection_mode` enabled will thus generate the `threshold_dump` file.

 
3. Auto mode:

    - This mode accepts threshold dump file(output of threshold detection mode) for threshold value.
    - This mode will continuously monitor the CPU stats, counters and handoff queue drops over the period of time. 
    - Meanwhile, the parsed value will be checked against the trigger value(from threshold_dump file) for threshold hit.
    - This monitoring will continue until threshold hits and those monitored dump will be zipped every time.
    - The `window_size` property will determine the number of last x valid zip to be maintained. 
    - The moment it hits, the perf profiling will gets initiated.
    - The critical threads have been identified and analysed as mentioned and the potential root cause report will be generated.
    - This entire process will continue until `consecutive_threshold_exceed_limit` expires.


### Output

### Getting started
1. Install the tool in the edge device under test
2. How to run 
  
   - Normal Mode:
   
          python index.py
          
   - Threshold detection mode
   
          python index.py -T
          Sub-options:
              -o -> Output file for dumping threshold
              -d -> Total duration

   - Auto mode:
   
          python index.py -A
          Sub-options:
              -i -> input threshold dump file
              -m -> preference mode (trigger value from value-based or bandwidth-based list)
              -w -> window size
              -l -> consecutive threshold exceed limit
              
   - Offline mode:
   
          python index.py -F <zip file>
              
