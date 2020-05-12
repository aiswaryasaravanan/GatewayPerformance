import sys
sys.path.append('perf_analysis_tool')

import os

import global_variable
import utils

if global_variable.auto_mode:
    file_name = global_variable.threshold_dump_file
    if os.path.exists(file_name):
        threshold_dump = utils.load_data(file_name)
    else:
        print('file not found... try running the tool with threshold_detection_mode first')
        exit()
