#
# Dumpey util functions
#

import subprocess as spc
import os
import re
import time


REMOTE_HEAP_DUMP_PATH = '/sdcard/_dumpey_hprof_tmp'

#
# PUBLIC API
#


def install(apk_path, *devices):
    if not devices:
        devices = _attached_devices()


def uninstall(package, *devices):
    pass


def list_packages(regex=None, *devices):
    if not devices:
        devices = _attached_devices()
    for device in devices:
        packages = _package_list(regex, device)
        fancy_print(ShellColors.HEADER, 'List of packages on %s:', device)
        print '\n'.join(packages)


def pull_apk(package, local_dir, *devices):
    if not devices:
        devices = _attached_devices()
    for device in devices:
        paths = _adb_decor(['shell', 'pm', 'path', package], device,
                           _decor_package)
        if len(paths) > 1:
            raise DumpeyException(
                'Multiple paths available: %s' % _to_str(paths))
        _pull_apk_from_path(paths[0], local_dir, device)


def _pull_apk_from_path(remote, local_dir, device):
    filename = _device_as_alnum(device) + '_' + os.path.basename(remote)
    local = os.path.join(local_dir, filename)
    _adb(['pull', '-p', remote, local], device)
    fancy_print(ShellColors.BOLD, 'Apk downloaded to %s', local)


def monkey(package, seed=123, events=1000, before=None, after=None, *devices):
    if not devices:
        devices = _attached_devices()
    for device in devices:
        if before:
            before(package, device)
        _adb(['shell', 'monkey', '-p', package, '-s', str(seed), str(events)],
             device)
        if after:
            after(package, device)


def dump_heap(package, local, *devices):
    if not devices:
        devices = _attached_devices()
    for device in devices:
        _dump(package, local, device)


def _dump(package, local, device):
    if _api_version(device) < 11:
        pass
    if os.path.isfile(os.path.abspath(local)) and os.path.isdir(
            os.path.abspath(local)):
        print 'WTF, directory'
        pass
    pid = _pid(package, device)
    if not pid:
        pass

    remote = REMOTE_HEAP_DUMP_PATH
    _adb(['shell', 'rm -f', remote], device)
    _adb(['shell', 'am', 'dumpheap', str(pid), remote], device)

    size = -1
    while True:
        time.sleep(.500)
        temp = _file_size(remote, device)
        if temp <= size:
            break
        size = temp
    local_dump = local + '-nonconv'
    _adb(['pull', '-p', remote, local_dump], device)
    abs1 = os.path.abspath(local_dump)
    abs2 = os.path.abspath(local)
    spc.check_call(['hprof-conv', abs1, abs2])
    os.remove(abs1)


#
# PRIVATE API
#

def _decor(output, cleanup=lambda l: l.strip()):
    splits = output.split('\n')
    lines = []
    for s in splits:
        l = s.strip()
        if l:
            lines.append(cleanup(l))
    return lines


def _decor_package(output):
    return _decor(output, lambda l: l.split('package:')[1])


def _adb(args, device=None):
    adb = ['adb', '-s', device] if device else ['adb']
    command = adb + args
    process = spc.Popen(command, stdout=spc.PIPE)
    output, err = process.communicate()
    exit_val = process.poll()
    if exit_val:
        raise DumpeyException('Command %s failed with an exit status '
                              '%d: %s' % command, exit_val, err)
    return output


def _adb_decor(args, device=None, decorator=_decor):
    return decorator(_adb(args, device))


def _attached_devices():
    device_list = _adb_decor(['devices'])[1:]
    return [d.split('\tdevice')[0] for d in device_list if d]


def _api_version(device):
    return _adb(['shell', 'getprop', 'ro.build.version.sdk'], device).strip()


def _file_size(filename, device):
    out = _adb(['shell', 'ls -l', filename], device).strip()
    return _split_wspace(out)[3]


def _package_list(regex, device):
    packages = _adb_decor(['shell', 'pm', 'list', 'packages'], device,
                          _decor_package)
    return [p for p in packages if regex.search(p)] if regex else packages


def _pid(package, device):
    out = _adb_decor(['shell', 'ps'], device)
    info = [p.strip() for p in out if package in p]
    if not info:
        raise DumpeyException('No PID found. Is your process running?')
    elif len(info) > 1:
        raise DumpeyException(
            'Multiple options available: %s' % _to_str(info))
    result = info[0]
    return _split_wspace(result)[1]


def _split_wspace(string):
    return re.sub(' +', ' ', string).split(' ')


def _device_as_alnum(device):
    return re.sub(r'\W+', '_', device)


def _to_str(lst):
    return ', '.join(lst)


class ShellColors:
    def __init__(self):
        raise Exception('instantiation not allowed')

    HEADER = '\033[95m'
    OK_BLUE = '\033[94m'
    OK_GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def fancy_print(shell_color, string_format, *string_args):
    message = string_format % string_args
    print shell_color + message + ShellColors.END


class DumpeyException(Exception):
    pass


if __name__ == "__main__":
    print _attached_devices()
    # print os.path.dirname(os.path.realpath(__file__))

    # regex = re.compile("tslamic*", re.IGNORECASE)
    # pck = list_packages(regex, '192.168.56.119:5555')
    # print pck

    # print _pid('labeler.tslamic.com.labeler','192.168.56.119:5555')
    #print _file_size('/sdcard/Pictures/Screenshots/Screenshot_2015-04-17-11-06-39.png','192.168.56.119:5555')

    #_dump('tslamic.fancybackground', 'test.hprof', '192.168.56.119:5555')

    #print _attached_devices()
    #pull_apk('tslamic.fancybackground', 'testing/')
    #dump_heap('tslamic.fancybackground', 'testing/')
    #print _package_list(regex,'192.168.56.119:5555')