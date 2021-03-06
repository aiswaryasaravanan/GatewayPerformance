import sys
sys.path.append('perf_analysis_tool')

import time
import datetime
from collections import OrderedDict

import utils

def get_hardware_info(manifest):
    manifest['deviceModel'] = utils.execute_command('cat /opt/vc/lib/python/hardwareinfo.py | grep DEVICE_MODEL').split(' = ')[1].split("'")[1]
    manifest['deviceFamily'] = utils.execute_command('cat /opt/vc/lib/python/hardwareinfo.py | grep DEVICE_FAMILY').split(' = ')[1].split("'")[1]
    manifest['deviceId'] = utils.execute_command('cat /opt/vc/lib/python/hardwareinfo.py | grep DEVICE_ID').split(' = ')[1].split("'")[1]
    return manifest

def get_build_info(manifest):
    manifest['version'] = utils.execute_command('edged -v | grep Version').split(':\t ')[1]
    manifest['buildHash'] = utils.execute_command('edged -v | grep Hash').split(':\t ')[1]
    manifest['buildRev'] = utils.execute_command('edged -v | grep rev').split(':\t ')[1]
    return manifest

def get_logical_id(manifest):
    manifest['logicalId'] = utils.execute_command('python /opt/vc/bin/getpolicy.py logicalId').split('"')[1]
    return manifest

def create_manifest():
    manifest = OrderedDict()

    manifest = get_hardware_info(manifest)
    manifest = get_build_info(manifest)
    manifest = get_logical_id(manifest)

    manifest['timestamp'] = time.time()
    manifest['datetime'] = str(datetime.datetime.now())
    manifest['id'] = None
    manifest['type'] = None
    manifest['requestId'] = None
    manifest['deviceType'] = None
    manifest['deviceCategory'] = None
    manifest['reason'] = None
    
    utils.write_file(manifest, 'temp_result/MANIFEST.json')