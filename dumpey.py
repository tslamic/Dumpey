"""
Dumpey
"""

__version__ = '1.0'

import subprocess as spc
import os
import re
import time
from random import randint
import argparse


# Actions


def install(apk_path, devices):
    """ Installs the apk on all specified devices. """
    if not devices:
        devices = attached_devices()
    for device in devices:
        adb(['install', apk_path], device)
        _fancy_info('%s installed on %s', apk_path, device)


def uninstall(package, devices):
    """ Uninstalls the package on all specified devices. """
    if not devices:
        devices = attached_devices()
    for device in devices:
        adb(['uninstall', package], device)
        _fancy_info('%s uninstalled from %s', package, device)


def pull_apk(package, local_dir, devices):
    """ Downloads the apk of a specific package. """
    if not devices:
        devices = attached_devices()
    for device in devices:
        paths = adb(['shell', 'pm', 'path', package], device, _decor_package)
        if len(paths) > 1:
            _fancy_warning('Multiple paths available on %s: %s' % device,
                           _to_str(paths))
            return
        target_path = paths[0]
        pull_apk_from_path(target_path, local_dir, device)


def pull_apk_from_path(remote, local_dir, device):
    """ Downloads the apk from a given remote path. """
    name = _device_safe_name(device) + '_' + os.path.basename(remote)
    local_file = os.path.join(local_dir, name)
    adb(['pull', '-p', remote, local_file], device)
    _fancy_info('Apk from %s downloaded to %s', device, local_file)


def monkey(package, devices, seed=None, events=None, before=None, after=None):
    """ Runs the monkey stress test. """
    if not devices:
        devices = attached_devices()
    if seed is None:
        seed = randint(1000, 10000)
    if events is None:
        events = 1000
    for device in devices:
        if before:
            before(package, device)
        _fancy_info('Kicking off monkey (seed=%d, events=%d) on %s '
                    'for package %s', seed, events, device, package)
        adb(['shell', 'monkey', '-p', package, '-s', str(seed), str(events)],
            device)
        if after:
            after(package, device)


def dump_heap(package, local_file, devices):
    """ Creates and downloads a heap dump of a given package. """
    if not devices:
        devices = attached_devices()
    for device in devices:
        dump_heap_on_single_device(package, local_file, device)


REMOTE_HEAP_DUMP_PATH = '/sdcard/_dumpey_hprof_tmp'


def dump_heap_on_single_device(package, local_file, device):
    """ Creates and downloads a heap dump of a given package. """
    if device is None:
        raise Exception('no device')
    api = api_version(device)
    if api < 11:
        _fancy_warning('Heap dumps are only available on API > 10. '
                       'Device %s is %d' % device, api)
        return
    pid_num = pid(package, device)
    remote = REMOTE_HEAP_DUMP_PATH
    adb(['shell', 'rm', '-f', remote], device)
    adb(['shell', 'am', 'dumpheap', str(pid_num), remote], device)

    # dumpheap runs as a daemon. We have to wait for it to
    # finish, so check the tmp file size continuously and stop
    # when it's not changing anymore.
    size = -1
    while True:
        time.sleep(.500)
        temp = _file_size(remote, device)
        if temp <= size:
            break
        size = temp

    local_file_dump = local_file + '-nonconv'
    adb(['pull', '-p', remote, local_file_dump], device)
    local_file_dump_abs = os.path.abspath(local_file_dump)
    local_file_abs = os.path.abspath(_hprof_file_name(local_file, device))
    spc.check_call(['hprof-conv', local_file_dump_abs, local_file_abs])
    os.remove(local_file_dump_abs)


# Helpers


def adb(args, device=None, decor=None):
    """ Executes an adb command. """
    head = ['adb', '-s', device] if device else ['adb']
    command = head + args
    process = spc.Popen(command, stdout=spc.PIPE)
    output, err = process.communicate()
    exit_val = process.poll()
    if exit_val:
        raise Exception('Failed to execute "%s", status=%d, err=%s'
                        % (_to_str(command, ' '), exit_val, err))
    return decor(output) if decor else output


def attached_devices():
    """ Returns a list of currently attached devices. """
    device_list = adb(['devices'], decor=_decor_split)[1:]
    return [d.split('\tdevice')[0] for d in device_list if d]


def package_list(devices, regex=None):
    """ Returns a dict with install packages on each device. """
    if not devices:
        devices = attached_devices()
    return {device: package_list_on_single_device(regex, device) for device in
            devices}


def api_version(device):
    """ Returns the Android SDK version a given device is running. """
    return adb(['shell', 'getprop', 'ro.build.version.sdk'], device).strip()


def package_list_on_single_device(regex, device):
    """ Lists the packages conforming to the regex on a specified device. """
    if device is None:
        raise Exception('no device')
    packages = adb(['shell', 'pm', 'list', 'packages'], device, _decor_package)
    return [p for p in packages if regex.search(p)] if regex else packages


def pid(package, device):
    """ Returns the package process ID on a specified device. """
    out = adb(['shell', 'ps'], device, _decor_split)
    processes = [p.strip() for p in out if package in p]
    if not processes:
        raise Exception('No process found for %s. '
                        'Is your app running?' % package)
    if len(processes) > 1:
        raise Exception('Multiple processes for %s: %s.'
                        % package, _to_str(processes))
    process_target = processes[0]
    return _split_whitespace(process_target)[1]


# Private helpers


def _file_size(file_path, device):
    """ Returns the size of a file on a given device. """
    out = adb(['shell', 'ls', '-l', file_path], device)
    if out.startswith(file_path):
        raise Exception('%s not found' % file_path)
    return _split_whitespace(out)[3]


def _decor_split(output, cleanup=None):
    splits = output.split('\n')
    return [cleanup(s) if cleanup else s.strip() for s in splits if s.strip()]


def _decor_package(output):
    return _decor_split(output, lambda l: l.strip().split('package:')[1])


def _split_whitespace(string):
    return re.sub(' +', ' ', string).split(' ')


def _device_safe_name(device):
    return re.sub(r'\W+', '_', device)


def _hprof_file_name(local_file, device):
    hprof = '.hprof'
    if local_file.endswith(hprof):
        local_file = local_file[:-len(hprof)]
    return local_file + '_' + _device_safe_name(device) + hprof


def _to_str(lst, delimiter=', '):
    return delimiter.join(lst)


SHELL_COLOR_LT_BLUE = '\033[94m'
SHELL_COLOR_WARNING = '\033[93m'
SHELL_COLOR_END = '\033[0m'


def _fancy_print(shell_color, string_format, *string_args):
    message = string_format % string_args
    print shell_color + message + SHELL_COLOR_END


def _fancy_warning(string_format, *string_args):
    _fancy_print(SHELL_COLOR_WARNING, string_format, *string_args)


def _fancy_info(string_format, *string_args):
    _fancy_print(SHELL_COLOR_LT_BLUE, string_format, *string_args)


def main():
    no_regex = '__no__regex__'
    parser = argparse.ArgumentParser(
        description='Dumpey description'
    )
    parser.add_argument('-i', '--install', metavar='APK',
                        help='install the apk')
    parser.add_argument('-u', '--uninstall', metavar='PACKAGE',
                        help='uninstall the package')
    parser.add_argument('-a', '--apk', nargs=2,
                        metavar=('PACKAGE', 'LOCAL_DIR'),
                        help='download the apk associated with the package')
    parser.add_argument('-m', '--monkey', nargs='+',
                        metavar=('PACKAGE', 'ARGS'),
                        help='runs monkey')
    parser.add_argument('-e', '--heapdump', nargs=2,
                        metavar=('PACKAGE', 'LOCAL'),
                        help='dumps heap')
    parser.add_argument('-l', '--list', nargs='?', const=no_regex,
                        metavar='REGEX',
                        help='prints installed packages, '
                             'Filtered by the regex, if given.')
    parser.add_argument('-d', '--devices', nargs='+', metavar='SERIAL',
                        help='devices to execute on. '
                             'If not given, all attached devices will be used.')
    args = parser.parse_args()

    print args

    devices = args.devices if args.devices else attached_devices()
    if args.install:
        install(args.install, devices)
    if args.uninstall:
        uninstall(args.uninstall, devices)
    if args.apk:
        pull_apk(args.apk[0], args.apk[1], devices)
    if args.monkey:
        print args.monkey
    if args.heapdump:
        dump_heap(args.heapdump[0], args.heapdump[1], devices)
    if args.list:
        regex = None
        if not no_regex == args.list and args.list.strip():
            regex = re.compile(args.list)
        print package_list(devices, regex)


        # try:
        # if args.install:
        # install(args.install, devices)
        # if args.uninstall:
        # uninstall(args.uninstall, devices)
        # if args.apk:
        # pull_apk(args.apk, devices)
        # if args.monkey:
        # print args.monkey
        # if args.heapdump:
        # package = args.heapdump[0]
        # local = args.heapdump[1]
        # dump_heap(package, local, devices)
        #     if args.list:
        #         regex = None
        #         if not no_regex == args.list and args.list.strip():
        #             regex = re.compile(args.list)
        #         print package_list(regex, devices)
        # except Exception as e:
        #     print "Error: " + str(e)


if __name__ == "__main__":
    # "tslamic.github.com.delightfulhomedrawable"
    # "/Users/tadejslamic/Development/DelightfulHomeDrawable/app/build/outputs/apk/app-debug.apk"
    # "/Users/tadejslamic/Documents/reversed/dump.hprof"
    # r = re.compile("tslamic")
    # pull_apk("com.sec.android.app.launcher", "/Users/tadejslamic/Documents/reversed")
    main()