import time
import datetime

import utils
from collections import OrderedDict

def getHardwareInfo(manifest):
    manifest['deviceModel'] = utils.executeCommand('cat /opt/vc/lib/python/hardwareinfo.py | grep DEVICE_MODEL').split(' = ')[1].split("'")[1]
    manifest['deviceFamily'] = utils.executeCommand('cat /opt/vc/lib/python/hardwareinfo.py | grep DEVICE_FAMILY').split(' = ')[1].split("'")[1]
    manifest['deviceId'] = utils.executeCommand('cat /opt/vc/lib/python/hardwareinfo.py | grep DEVICE_ID').split(' = ')[1].split("'")[1]
    return manifest

def getBuildInfo(manifest):
    manifest['version'] = utils.executeCommand('edged -v | grep Version').split(':\t ')[1]
    manifest['build'] = utils.executeCommand('edged -v | grep Hash').split(':\t ')[1]
    return manifest

def getLogicalId(manifest):
    manifest['logicalId'] = utils.executeCommand('python /opt/vc/bin/getpolicy.py logicalId').split('"')[1]
    return manifest

def createManifest():
    manifest = OrderedDict()

    manifest = getHardwareInfo(manifest)
    manifest = getBuildInfo(manifest)
    manifest = getLogicalId(manifest)

    manifest['timestamp'] = time.time()
    manifest['datetime'] = str(datetime.datetime.now())
    manifest['id'] = None
    manifest['type'] = None
    manifest['requestId'] = None
    manifest['deviceType'] = None
    manifest['deviceCategory'] = None
    manifest['reason'] = None
    
    utils.writeFile(manifest, 'tempResult/MANIFEST.json')