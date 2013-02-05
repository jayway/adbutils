#!/usr/bin/env python

"""
A Python module containing functionality for communicating through ADB.
If you only have one attached device, you will not need to specify which to run the command on.

"""

import logging
import os
import re
import subprocess
import signal
import thread
import time

__author__    = 'Andreas Nilsson'
__email__     = 'andreas.nilsson@jayway.com'
__copyright__ = "Copyright 2013, Jayway"
__license__   = 'Apache 2.0'

#Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

#Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

#Setup Console logging
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)

#Add logger handlers
logger.addHandler(ch)


#ADB-path
_adb_bin = '/Users/Enighma/android-sdk-macosx/platform-tools/adb'


#Constants
REBOOT_BOOTLOADER = 'bootloader'
REBOOT_RECOVERY   = 'recovery'


class AdbDevice(object):
    TYPE_EMULATOR = 'TYPE_EMULATOR'
    TYPE_IP       = 'TYPE_IP'
    TYPE_USB      = 'TYPE_USB'
    TYPE_UNKNOWN  = 'UNKNOWN'

    _usb_identifier = 'usb'

    def __init__(self, id, meta):
        self.id = id
        self.meta = meta
        self.type = self._parse_type()

    def _parse_type(self):
        if self.get_usb_id():
            return self.TYPE_USB
        elif 'emulator' in self.id:
            return self.TYPE_EMULATOR
        elif self._is_ip(self.id):
            return self.TYPE_IP
        else:
            return self.TYPE_UNKNOWN


    def _is_ip(self, id):
        return bool(re.findall(r'[0-9]+(?:\.[0-9]+){3}', id))

    def __str__(self):
        return 'ADB Device: %s\ttype: %s\tmeta: %s' % (self.id, self.type, self.meta)

    def get_model(self):
        return self.meta.get('model', None)

    def get_product(self):
        return self.meta.get('product', None)

    def get_device(self):
        return self.meta.get('device', None)

    def get_usb_id(self):
        return self.meta.get('usb', None)

    def get_device_type(self):
        return self.type

    def get_meta(self):
        return self.meta

    def get_id(self):
        return self.id


class ErrorInfo(object):
    exception      = None
    message    = None
    args       = None
    cmd        = None
    returncode = None

    def __init__(self, exception):
        self.exception = exception

        if exception:
            self.message    = exception.message
            self.args       = exception.args
            self.returncode = exception.returncode
            self.cmd        = exception.cmd


    def __str__(self):
        return 'args: %s; return code: %s; cmd: %s; message: %s' % \
               (self.exception.args, self.exception.returncode, self.exception.cmd, self.exception.message)

    def get_exception(self):
        return self.exception



_error_info = None

def _reset_error():
    _error_info = None

def _set_error_info(called_process_error):
    global _error_info
    _error_info = ErrorInfo(called_process_error)

def get_error_info():
    return _error_info


def error():
    print 'error funct'
    pass

def run_adb_command(command, device=None):
    _reset_error()

    adb_device_cmd = ' -s %s' % device.id if device else ''
    cmd = _adb_bin + '' + adb_device_cmd + ' ' + command

    logger.debug('adb cmd: %s', cmd)

    try:
        #TODO replace check_output with Popen to handle when shell is becoming locked with a print loop
        output = subprocess.check_output(cmd, shell=True)
    except subprocess.CalledProcessError as e:
        output = ''
        logger.error(str(e))
        _set_error_info(e)


    return output


def run_instrument(package, instrument_runner='android.test.InstrumentationTestRunner', class_name=None):
    '''
    Return the output from ADB when running the defined instrument in a shell.

    Keyword arguments:
    package -- The package whom the TestRunner belongs to.
    instrument_runner -- Your Custom testrunner (default android.test.InstrumentationTestRunner)
    class_name -- The test class to execute. (default None)
    '''
    class_str  = "-e class %s/%s" % (package, class_name) if class_name else ''

    cmd = r'shell "am instrument -w %(clazz)s %(package)s/%(test_runner)s"' %\
          {'package': package,'test_runner': instrument_runner, 'clazz': class_str, }

    logger.debug("Running cmd: %s", cmd)

    return  run_adb_command(cmd)


def kill_server():
    return run_adb_command('kill-server')


def start_server():
    return run_adb_command('start-server')

def restart_server():
    kill_server()
    time.sleep(0.5)
    return  'daemon started successfully' in start_server()


def wait_for_device(device):
    run_adb_command('wait-for-device', device)
    # _run_on_specific_device('wait-for-device', device)


def install(app_name, device=None):
    return 'Success' in _run_on_specific_device('install %s' % app_name, device)

def uninstall(app_name, device):
    return 'Success' in _run_on_specific_device('uninstall %s' % app_name, device)


def _run_on_specific_device(cmd, device):
    output = 'Failure'
    n_devices = len(get_adb_devics())
    if n_devices > 1 and not device:
        logger.info('You need to specify which device to install onto')
    elif n_devices == 0:
        logger.info('There are no connected devices')
    else:
        output = run_adb_command(cmd, device)

    return output


def _create_adb_device_from_line(line):
    adb_device = None

    skip_line_args = ['List of devices attached']
    do_skip_line =  any(word in line for word in skip_line_args)
    split = line.split()
    if split and not do_skip_line:

        id = split[0]
        meta = {}

        for key_value in split[2:]:
            if ':' in key_value:
                key, value = key_value.split(':')
                meta[key] = value


                adb_device = AdbDevice(id, meta)

        # if id:
        #     logger.debug('Device: %s; %s', id, meta)

    return adb_device


def get_adb_devics():
    devices = []
    output = run_adb_command('devices -l')
    for line in output.splitlines():
        adb_device = _create_adb_device_from_line(line)

        if adb_device:
            devices.append(adb_device)


    logger.debug('Attached Devices: %d', len(devices))
    return devices

def restart_as_root(device):
    #TODO test with non root device.
    return  _run_on_specific_device('root', device)

def set_adb_path(path):
    global _adb_bin
    _adb_bin = path


def remount_sys_part(device):
    return _run_on_specific_device('remount', device)


def reboot(device, reboot_into=None, do_wait_for_device=False):
    cmd = 'reboot'
    if reboot_into is REBOOT_BOOTLOADER or reboot_into is REBOOT_RECOVERY:
        cmd += ' ' + reboot_into

    output = run_adb_command(cmd, device)

    if do_wait_for_device:
        wait_for_device(device)

    return output


def push(local, remote, device=None):
     output =  _run_on_specific_device('push %s %s' % (local, remote) , device)
     return not output.startswith('failed to copy')

def pull(remote, local=None, device=None):
    cmd = 'pull %s' % remote
    if local:
        cmd += ' ' + local

    return _run_on_specific_device(cmd, device)


def connect(ip, port=5555):
    return 'unable to connect' not in run_adb_command('connect %s:%d' % (ip,port))


def disconnect(ip='', port=5555):
    return run_adb_command('disconnect %s:%d' % (ip,port))


if __name__ == '__main__':

    logger.info('Connect: %s', disconnect('192.168.2.2'))
    logger.info('Connect: %s', connect('192.168.2.2'))


    # devices = get_adb_devics()
    # if devices:
    #     dev = devices[0]
    #
    # for d in devices:
    #     print str(d)

    # app_path = '/Users/Enighma/projects/graphview/bin/GraphActivity.apk'
    # app_name = 'com.jayway.graph'
    # uninstall(app_name, devices[0])
    # logger.info('Uninstalled: %s', uninstall(app_name, devices[0]))
    # logger.info('Installed: %s', install(app_path))
    # logger.info('Installed: %s', install(app_path, devices[0]))

    # restart_server()

    # wait_for_device(dev)

    # print restart_as_root(dev)

    # reboot(dev, do_wait_for_device=True)
    #
    # reboot(dev, reboot_into=REBOOT_RECOVERY , do_wait_for_device=True)

    # reboot(dev, reboot_into=REBOOT_BOOTLOADER , do_wait_for_device=True)

    # local  = '../tests/test.txt'
    # remote = '/storage/sdcard1/test.txt'
    # remote = '/moo/test.txt'
    # print os.listdir(local)
    # logger.info(push(local, remote, dev))
    # logger.info(pull(remote, device=dev))
    # if get_error_info():
    #     print 'found error'
    # else:
    #     print 'found no error'



