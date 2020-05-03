## Perf-Analysis Tool

### Why this tool:
   This Perf-Analysis tool will identify the performance issue in the edge and provides the potential root cause report. This make use of `perf` tool which is a linux profiler tool.
   
### Input:

   The input to this Perf-Analysis tool is a json file that contains the following,
   
   - Total Duration and sample frequency interval
   - Output directory
   - List of processes, commands and counters to monitor
   - List of what to analyse
   - Diag tool(here perf) and its meta data

### How it works:
  This tool will monitor CPU profiling data, counters and handoff queue drops over the period of time(provided the frequency interval) and dump them into a JSON format. CPU stacks are profiled using `perf record` and stored in a binary file `perf.data` which can later be analysed. All the dumped file will be zipped later. Meanwhile the top critical threads(threads with maximum cpu utilization/drops) will be identified. Once the perf record is done, the reports will be generated for the corresponding suspected critical threads using  `perf report`. This is the normal behaviour of the tool.


#### Various modes:

1. Offline mode:

    This mode accepts the monitored zip file and thus allows offline processing. The inputted zip file will be unzipped, and the rest of the work will make use of the this inputted file.

1. Threshold-detection-mode:

    Running the tool with `threshold_detection_mode` enabled will generate the threshold dump file, that contains the trigger value along with the bandwidth information for every process, queues and counters. This will monitor the device for a predefined number of times and maintain the trigger value in separate list, bandwidth based and value based, with top x value.
 
1. Auto-mode:
 
   This mode will continuously monitor the device and check for threshold hits. The moment it hits, CPU stacks will be profiled using `perf`. This mode makes use of the threshold file from `threshold_detection_mode`. `Window size` will be maintained to manage the number of monitored zip file. `consecutive threshold exceed limit` limits the number of times the report being generated. It determines when to quit the tool.


### Output

### Getting started
1. Install the tool in the edge device under test
1. How to run 
  
   - Normal Mode:
   
          python index.py
          
   - Threshold detection mode
   
          python index.py -T
          Sub-options:
              -o -> Output file for dumping threshold
              -s -> Number of sample
   - Auto mode:
   
          python index.py -A
          Sub-options:
              -i -> input threshold dump file
              -m -> preference mode (trigger value from value-based or bandwidth-based list)
              -w -> window size
              -l -> consecutive threshold exceed limit
              
   - Offline mode:
   
          python index.py -F <zip file>
              
