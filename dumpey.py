"""
Dumpey
"""

__version__ = '1.0'

import os
import re
import time
import subprocess
import argparse
from random import randint


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


# FIXME local_dir can be None - then use os.getcwd()
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


# FIXME local_dir can be None - then use os.getcwd()
def pull_apk_from_path(remote, local_dir, device):
    """ Downloads the apk from a given remote path. """
    name = _alphanum_str(device) + '_' + os.path.basename(remote)
    local_file = os.path.join(local_dir, name)
    adb(['pull', '-p', remote, local_file], device)
    _fancy_info('Apk from %s downloaded to %s', device, local_file)


def monkey(package, devices,
           seed=None, events=None, before=None, after=None, log=True):
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
        if log:
            _fancy_info('Kicking off monkey (seed=%d, events=%d) on %s '
                        'for package %s', seed, events, device, package)
        adb(['shell', 'monkey', '-p', package, '-s', str(seed), str(events)],
            device)
        if after:
            after(package, device)


# FIXME local_dir can be None - then use os.getcwd()
def dump_heap(package, local_dir, devices):
    """ Creates and downloads a heap dump of a given package. """
    if not devices:
        devices = attached_devices()
    for device in devices:
        dump_heap_on_single_device(package, local_dir, device)


_REMOTE_HEAP_DUMP_PATH = '/sdcard/_dumpey_hprof_tmp'


# FIXME local_dir can be None - then use os.getcwd()
def dump_heap_on_single_device(package, local_dir, device, append=None):
    """ Creates and downloads a heap dump of a given package. """
    if device is None:
        raise Exception('no device')
    api = api_version(device)
    if api < 11:
        _fancy_warning('Heap dumps are only available on API > 10. '
                       'Device %s is %d' % device, api)
        return
    pid_num = pid(package, device)
    remote = _REMOTE_HEAP_DUMP_PATH
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

    name = _alphanum_str(device) + '_' + _alphanum_str(package)
    if append:
        name += '_' + append
    local_file = os.path.join(local_dir, name + '.hprof')
    local_file_nonconv = local_file + '-nonconv'
    adb(['pull', '-p', remote, local_file_nonconv], device)
    subprocess.check_call(['hprof-conv', local_file_nonconv, local_file])
    os.remove(local_file_nonconv)
    _fancy_info('Converted hprof file downloaded to %s', local_file)


# Helpers


def adb(args, device=None, decor=None):
    """ Executes an adb command. """
    head = ['adb', '-s', device] if device else ['adb']
    command = head + args
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    output, err = process.communicate()
    exit_val = process.poll()
    if exit_val:
        raise Exception('Failed to execute "%s", status=%d, err=%s'
                        % (_to_str(command, ' '), exit_val, err))
    return decor(output) if decor else output


def attached_devices():
    """ Returns a list of currently attached devices. """
    device_list = adb(['devices'], decor=_decor_split)[1:]
    devices = [d.split('\tdevice')[0] for d in device_list if d]
    if not devices:
        raise Exception('no devices attached')
    return devices


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


_MAX_PID_RETRIES = 3


def pid(package, device, retries=0):
    """ Returns the package process ID on a specified device. """
    out = adb(['shell', 'ps'], device, _decor_split)
    processes = [p.strip() for p in out if package in p]
    if not processes:
        # The app might be installed, but is not running.
        # To avoid manual start, try to run the monkey with a single event,
        # then re-query.
        if retries >= _MAX_PID_RETRIES:
            raise Exception('No process on %s found for %s. '
                            'Is your app installed?' % (device, package))
        monkey(package, [device], seed=0, events=1, log=False)
        return pid(package, device, retries + 1)
    if len(processes) > 1:
        raise Exception('Multiple processes for %s: %s.'
                        % package, _to_str(processes))
    process_target = processes[0]
    return _split_whitespace(process_target)[1]


def _file_size(file_path, device):
    """ Returns the size of a file on a given device. """
    out = adb(['shell', 'ls', '-l', file_path], device)
    if out.startswith(file_path):
        raise Exception('%s not found' % file_path)
    return _split_whitespace(out)[3]


def _decor_split(output, cleanup=None):
    """ Splits the output into lines and performs per-line cleanup. """
    splits = output.split('\n')
    return [cleanup(s) if cleanup else s.strip() for s in splits if s.strip()]


def _decor_package(output):
    """ Splits the output into lines and removes package: delimiter """
    return _decor_split(output, lambda l: l.strip().split('package:')[1])


def _split_whitespace(string):
    return re.sub(' +', ' ', string).split(' ')


def _alphanum_str(string):
    return re.sub(r'\W+', '_', string)


def _to_str(lst, delimiter=', '):
    """ Creates a user-friendly list string. """
    return delimiter.join(lst)


_SHELL_COLOR_LT_BLUE = '\033[94m'
_SHELL_COLOR_WARNING = '\033[93m'
_SHELL_COLOR_END = '\033[0m'


def _fancy_print(shell_color, string_format, *string_args):
    """ Prints a colored message. """
    message = string_format % string_args
    print shell_color + message + _SHELL_COLOR_END


def _fancy_warning(string_format, *string_args):
    _fancy_print(_SHELL_COLOR_WARNING, string_format, *string_args)


def _fancy_info(string_format, *string_args):
    _fancy_print(_SHELL_COLOR_LT_BLUE, string_format, *string_args)


_NO_REGEX_FLAG = '__no__regex__'


def _create_args_parser():
    """ Creates the argument parser for dumpey. """
    parser = argparse.ArgumentParser(
        description='Dumpey description'
    )
    parser.add_argument('-i', '--install',
                        metavar='APK',
                        help='installs the apk')
    parser.add_argument('-u', '--uninstall',
                        metavar='PACKAGE',
                        help='uninstalls the app with associated package name')
    parser.add_argument('-a', '--apk',
                        nargs=2,
                        metavar=('PACKAGE', 'LOCAL_DIR'),
                        help='''downloads the package apk to a specified
                                local directory''')
    parser.add_argument('-m', '--monkey',
                        # nargs='+',
                        nargs=argparse.REMAINDER,
                        metavar=('PACKAGE', 'ARGS'),
                        help='''runs the monkey on the given package name.
                                Accepts four additional arguments:
                                "s=(int)" denoting seed value, "e=(int)",
                                denoting number of events, "h=(b|a|ba)",
                                denoting heap dumps done before, after or
                                before and after monkey execution and "d=(dir)",
                                specifying the local directory where heap dumps
                                are downloaded to. All arguments are optional,
                                but specifying "h" requires "d" to be
                                given too.''')
    parser.add_argument('-e', '--heapdump',
                        nargs=2,
                        metavar=('PACKAGE', 'LOCAL_DIR'),
                        help='''downloads and converts a heap dump from
                                the given package.''')
    parser.add_argument('-l', '--list',
                        nargs='?',
                        metavar='REGEX',
                        const=_NO_REGEX_FLAG,
                        help='''prints the installed packages,
                                filtered by the regex, if specified.''')
    parser.add_argument('-d', '--devices',
                        nargs='+',
                        metavar='SERIAL',
                        help='''devices to run this command on.
                                If missing, all attached devices
                                will be used.''')
    return parser


def _parse_monkey(package, args, devices):
    if not args:
        monkey(package, devices)
        return
    parser = argparse.ArgumentParser(prog='-m', add_help=False)
    parser.add_argument('-s', '--seed', type=int)
    parser.add_argument('-e', '--events', type=int)
    parser.add_argument('-h', '--heap', choices=['b', 'a', 'ba', 'ab'])
    parser.add_argument('-d', '--dir', type=argparse.FileType('w'))
    monkey_args = parser.parse_args(args)
    monkey(package, devices, monkey_args.seed, monkey_args.events,
           monkey_args.heap, monkey_args.dir)


# TODO: maybe there's an easier way to do this with argparse
def _handle_monkey(package, args, devices):
    """ Parses the additional monkey params, if any, and executes it."""
    if not args:
        monkey(package, devices)
        return

    try:
        args_dict = dict(a.strip().split('=') for a in args)
    except ValueError as e:
        raise type(e)('ensure monkey params are properly set, for example: '
                      '-m your.package.name s=(int) e=(int) d=(b|a|ba) d=(dir)')
    s = args_dict.get('s')
    e = args_dict.get('e')
    h = args_dict.get('h')
    d = args_dict.get('d')

    try:
        seed = int(s) if s else None
        events = int(e) if e else None
    except ValueError as e:
        raise type(e)('s and e monkey params only accept integer values.')

    before = None
    after = None
    if h:
        if not d:
            raise Exception('local directory for monkey heap dumps missing, '
                            'add "d=(path)" param')
        if 'b' in h:
            before = lambda pkg, dev: dump_heap_on_single_device(pkg, d,
                                                                 dev, 'before')
        if 'a' in h:
            after = lambda pkg, dev: dump_heap_on_single_device(pkg, d,
                                                                dev, 'after')
    monkey(package, devices,
           seed=seed, events=events, before=before, after=after)


def _handle_list(regex_string, devices):
    regex = None
    if not _NO_REGEX_FLAG == regex_string and regex_string.strip():
        regex = re.compile(regex_string)
    packages_dict = package_list(devices, regex)
    for device in packages_dict:
        _fancy_info('Installed packages on %s:', device)
        for package in packages_dict[device]:
            print package


def main():
    parser = _create_args_parser()
    args = parser.parse_args()
    devices = args.devices if args.devices else attached_devices()
    if args.install:
        install(args.install, devices)
    if args.uninstall:
        uninstall(args.uninstall, devices)
    if args.apk:
        pull_apk(args.apk[0], args.apk[1], devices)
    if args.monkey:
        _parse_monkey(args.monkey[0], args.monkey[1:], devices)
        # _handle_monkey(args.monkey[0], args.monkey[1:], devices)
    if args.heapdump:
        dump_heap(args.heapdump[0], args.heapdump[1], devices)
    if args.list:
        _handle_list(args.list, devices)


if __name__ == "__main__":
    main()