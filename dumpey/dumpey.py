"""
Dumpey is an Android Debug Bridge utility tool. It helps you

* pull installed APKs
* pull converted memory dumps
* run the monkey with memory dumps before and after it
* install and uninstall packages
* take screenshots

on all attached devices, or the ones you specify.
"""

__version__ = '1.0.0'

import subprocess
import argparse
import random
import time
import sys
import re
import os

_MONKEY_SEED_MIN = 1000
_MONKEY_SEED_MAX = 10000
_MONKEY_EVENTS = 1000

_NO_REGEX_FLAG = '__no__regex__'

_SHELL_COLOR_LT_BLUE = '\033[94m'
_SHELL_COLOR_WARNING = '\033[91m'
_SHELL_COLOR_END = '\033[0m'


def _cmd(args):
    """
    Executes a command line command.
    """
    process = subprocess.Popen(args, stdout=subprocess.PIPE)
    output, err = process.communicate()
    returncode = process.poll()
    if returncode:
        raise Exception("failed to execute '%s', status=%d, err=%s"
                        % (_to_str(args, " "), returncode, err))
    return output


def adb(args, device=None, decor=None):
    """
    Executes an adb command.
    """
    head = ['adb', '-s', device] if device else ['adb']
    command = head + args
    output = _cmd(command)
    return decor(output) if decor else output


def attached_devices():
    """
    Returns a list of currently attached devices.
    Raises an exception if none are available.
    """
    device_list = adb(['devices'], decor=_decor_split)[1:]
    devices = [d.split('\tdevice')[0] for d in device_list if d]
    if not devices:
        raise Exception('no devices attached')
    return devices


def api_version(device, converter=None):
    """
    Returns the Android SDK version a given device is running on.
    """
    version = adb(['shell', 'getprop', 'ro.build.version.sdk'], device).strip()
    return converter(version) if converter else version


def install(local_path=None, devices=None, recursive=False):
    """
    Installs the apk on all given devices.
    If local path is a directory, it browses through files, installing
    the ones ending with ".apk".
    If recursive is True, it does the same with each subdirectory it finds.
    """
    if local_path is None:
        local_path = os.getcwd()
    elif not os.path.isfile(local_path):
        raise Exception("%s does not exist" % local_path)
    if devices is None:
        devices = attached_devices()
    if os.path.isdir(local_path):
        _install_from_dir(local_path, devices, recursive)
    else:
        _install_from_file(local_path, devices)


def _install_from_dir(local_dir, devices, recursive):
    for item in os.listdir(local_dir):
        local = os.path.join(local_dir, item)
        if item.endswith(".apk"):
            _install_from_file(local, devices)
        elif recursive and os.path.isdir(local):
            _install_from_dir(local, devices, recursive)


def _install_from_file(local_file, devices):
    for device in devices:
        adb(['install', local_file], device)
        _inform('%s installed on %s', local_file, device)


def uninstall(package=None, regex=None, devices=None, force=False):
    """
    Uninstalls the package on all given devices.
    Either package or regex must be given.
    If force is True, any package fitting the regex will be uninstalled.
    If both package and regex are given, only package is considered.
    """
    _ensure_package_or_regex(package, regex)
    if devices is None:
        devices = attached_devices()
    if package is not None:
        for device in devices:
            _uninstall_package(package, device)
    else:
        _package_iter(regex, devices, _uninstall_package, force)


def _uninstall_package(package, device):
    adb(['uninstall', package], device)
    _inform('%s uninstalled from %s', package, device)


def pull_apk(package=None, regex=None, devices=None, local_dir=None,
             force=False):
    """
    Downloads the apk of a specific package.
    """
    _ensure_package_or_regex(package, regex)
    if devices is None:
        devices = attached_devices()
    if local_dir is None:
        local_dir = os.getcwd()
    if package is not None:
        for device in devices:
            _pull_apk(package, device, local_dir)
    else:
        _package_iter(regex, devices, _pull_apk, force, local_dir)


def _package_iter(regex, devices, f, force=False, *args):
    compiled_regex = re.compile(regex)
    for device in devices:
        packages = _package_list(device, compiled_regex)
        if not packages:
            _warn("nothing found for regex '%s' on %s", regex, device)
        elif len(packages) > 1 and not force:
            _warn("multiple apps found for regex '%s' on %s: %s", regex, device,
                  _to_str(packages))
        else:
            for package in packages:
                f(package, device, *args)


def pull(remote, local, device, show_progress=True):
    command = ['pull', '-p', '-a', remote, local]
    if not show_progress:
        command.pop(1)
    adb(command, device)


def _pull_apk(package, device, local_dir):
    paths = adb(['shell', 'pm', 'path', package], device, _decor_package)
    if not paths:
        _warn('path for package %s on %s not available', package, device)
    elif len(paths) > 1:
        _warn('multiple paths available on %s: %s', device, _to_str(paths))
    else:
        path = paths[0]
        name = _alphanum_str(device) + '_' + os.path.basename(path)
        local = os.path.join(local_dir, name)
        pull(path, local, device)
        _inform('apk from %s downloaded to %s', device, local)


_REMOTE_SCREENCAP_PATH = '/sdcard/_dumpey_screencap_tmp.png'


def _snapshot(device, local_dir):
    now = str(int(time.time()))
    name = _alphanum_str(device) + '_' + now + '.png'
    local_file = os.path.join(local_dir, name)
    remote = _REMOTE_SCREENCAP_PATH
    adb(['shell', 'screencap', remote])
    pull(remote, local_file, device, show_progress=False)
    remove_file(remote, device)
    _inform("screenshot downloaded to %s", local_file)


def single_snapshot(device, local_dir=None):
    if device is None:
        raise Exception('device not given')
    if local_dir is None:
        local_dir = os.getcwd()
    _snapshot(device, local_dir)


def snapshots(device, local_dir=None):
    if device is None:
        raise Exception('device not given')
    if local_dir is None:
        local_dir = os.getcwd()
    _inform("press enter to take a screenshot or [any key + enter] to exit")
    while sys.stdin.read(1) == "\n":
        _snapshot(device, local_dir)


def monkey(package, devices=None, seed=None, events=None, before=None,
           after=None, log=True):
    """
    Runs the monkey stress test.
    """
    if devices is None:
        devices = attached_devices()
    if seed is None:
        seed = random.randint(_MONKEY_SEED_MIN, _MONKEY_SEED_MAX)
    if events is None:
        events = _MONKEY_EVENTS
    for device in devices:
        if before:
            before(package, device)
        if log:
            _inform('starting monkey (seed=%d, events=%d) on %s '
                    'for package %s', seed, events, device, package)
        adb(['shell', 'monkey', '-p', package, '-s', str(seed), str(events)],
            device)
        if after:
            after(package, device)


def dump_heap(package=None, regex=None, devices=None, local_dir=None,
              force=False):
    """
    Creates and downloads a heap dump of a given package.
    """
    _ensure_package_or_regex(package, regex)
    if devices is None:
        devices = attached_devices()
    if local_dir is None:
        local_dir = os.getcwd()
    if package is not None:
        for device in devices:
            _dump_heap(package, device, local_dir)
    else:
        _package_iter(regex, devices, _dump_heap, force, local_dir)


_REMOTE_HEAP_DUMP_PATH = '/sdcard/_dumpey_hprof_tmp'


def _dump_heap(package, device, local_dir, append=None):
    api = api_version(device, converter=int)
    if api < 11:
        _warn('heap dumps are only available on API > 10, device %s is %d',
              device, api)
        return

    pid_str = pid(package, device)
    remote = _REMOTE_HEAP_DUMP_PATH

    remove_file(remote, device)
    adb(['shell', 'am', 'dumpheap', pid_str, remote], device)

    # dumpheap shell command runs as a daemon.
    # We have to wait for it to finish, so check the tmp file size
    # at timed intervals and stop when it's not changing anymore.
    # TODO: maybe this can be done better
    size = -1
    while True:
        time.sleep(.500)
        temp = file_size(remote, device)
        if temp <= size:
            break
        size = temp

    name = _alphanum_str(device) + '_' + _alphanum_str(package)
    if append:
        name = '%s_%s' % (name, append)
    local_file = os.path.join(local_dir, name + '.hprof')
    local_file_nonconv = local_file + '-nonconv'

    adb(['pull', '-p', remote, local_file_nonconv], device)
    _cmd(['hprof-conv', local_file_nonconv, local_file])
    os.remove(local_file_nonconv)
    remove_file(remote, device)
    _inform('converted hprof file available at %s', local_file)


def package_list(devices=None, regex=None):
    """
    Returns a dict with installed packages on each device.
    Filtered by the regex, if given.
    """
    if devices is None:
        devices = attached_devices()
    compiled = re.compile(regex) if regex else None
    return {device: _package_list(device, compiled) for device in devices}


def _package_list(device, compiled_regex):
    packages = adb(['shell', 'pm', 'list', 'packages'], device, _decor_package)
    return [p for p in packages if
            compiled_regex.search(p)] if compiled_regex else packages


def pid(package, device, force_open=True):
    """
    Returns the package process ID on a specified device.
    """
    out = adb(['shell', 'ps'], device, _decor_split)
    processes = [p.strip() for p in out if package in p]
    if not processes:
        if force_open:
            # The app might be installed, but is not running. Exec the monkey
            # with a single event, then re-query.
            monkey(package, [device], seed=0, events=1, log=False)
            return pid(package, device, force_open=False)
        raise Exception('no process on %s found for %s, is your app '
                        'installed?' % (device, package))
    elif len(processes) > 1:
        raise Exception('Multiple processes for %s: %s.'
                        % package, _to_str(processes))
    return _split_whitespace(processes[0])[1]


def file_size(remote_path, device):
    """
    Returns the size of a file on a given device.
    """
    out = adb(['shell', 'ls', '-l', remote_path], device)
    if out.startswith(remote_path):
        raise Exception('%s not found' % remote_path)
    return _split_whitespace(out)[3]


def remove_file(remote_path, device):
    """
    Removes the remote path from a device, if it exists.
    """
    adb(['shell', 'rm', '-f', remote_path], device)


def clear_data(package=None, regex=None, devices=None, force=False):
    """
    Clears the app data.
    """
    _ensure_package_or_regex(package, regex)
    if devices is None:
        devices = attached_devices()
    if package is not None:
        for device in devices:
            _clear_data(package, device)
    else:
        _package_iter(regex, devices, _clear_data, force)


def _clear_data(package, device):
    adb(["shell", "pm", "clear", package], device)


def reboot(devices):
    for device in devices:
        adb(["shell", "reboot"], device)


# Helpers

def _ensure_package_or_regex(package, regex):
    if package is None and regex is None:
        raise Exception("either package or regex must be given")


def _decor_split(output, cleanup=None):
    splits = output.split('\n')
    return [cleanup(s) if cleanup else s.strip() for s in splits if s.strip()]


def _decor_package(output):
    return _decor_split(output, lambda l: l.strip().split('package:')[1])


def _split_whitespace(string):
    return re.sub(' +', ' ', string).split(' ')


def _alphanum_str(string):
    return re.sub(r'\W+', '_', string)


def _to_str(lst, delimiter=', '):
    return delimiter.join(lst)


def _print(shell_color, string_format, *string_args):
    message = string_format % string_args
    print shell_color + message + _SHELL_COLOR_END


def _warn(string_format, *string_args):
    _print(_SHELL_COLOR_WARNING, string_format, *string_args)


def _inform(string_format, *string_args):
    _print(_SHELL_COLOR_LT_BLUE, string_format, *string_args)


def _dumpey_args_parser():
    parser = argparse.ArgumentParser(
        description="Dumpey, an Android Debug Bridge utility tool."
    )
    devices_parser = argparse.ArgumentParser(add_help=False)
    devices_parser.add_argument("-s",
                                "--serials",
                                nargs="+",
                                metavar="SERIAL",
                                help="Device serials to run the command on", )
    subparsers = parser.add_subparsers(title="Available commands",
                                       dest="sub",
                                       help="options provided by dumpey")

    install_parser = subparsers.add_parser("i", parents=[devices_parser],
                                           help="install APKs from a given path")
    install_parser.add_argument("-e", "--source", help="apk or directory path")

    uninstall_parser = subparsers.add_parser("u", parents=[devices_parser],
                                             help="uninstall apps")
    uninstall_parser.add_argument("")

    parser.add_argument('-u', '--uninstall',
                        metavar='PACKAGE',
                        help='uninstalls the app with associated package name')
    parser.add_argument('-a', '--apk',
                        nargs='+',
                        metavar=('PACKAGE', 'LOCAL_DIR'),
                        help='''downloads the package apk to a specified
                                local directory or current working directory''')
    parser.add_argument('-m', '--monkey',
                        nargs=argparse.REMAINDER,
                        metavar=('PACKAGE', 'ARGS'),
                        help='''runs the monkey on the given package name.
                                Accepts four additional arguments:
                                "-s=(int)" denoting seed value, "e=(int)",
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


def _handle_monkey(package, args, devices):
    if not args:
        monkey(package, devices)
        return

    parser = argparse.ArgumentParser(prog='-m', add_help=False)
    parser.add_argument('-s', '--seed', type=int)
    parser.add_argument('-e', '--events', type=int)
    parser.add_argument('-h', '--heap', choices=['b', 'a', 'ba', 'ab'])
    parser.add_argument('-d', '--dir', type=argparse.FileType('w'))
    monkey_args = parser.parse_args(args)
    print monkey_args

    before = after = None
    if monkey_args.heap:
        local_dir = monkey_args.dir if monkey_args.dir else os.getcwd()
        if 'b' in monkey_args.heap:
            before = lambda p, d: dump_heap(p, [d], local_dir, 'before')
        if 'a' in monkey_args.heap:
            after = lambda p, d: dump_heap(p, [d], local_dir, 'after')
    monkey(package, devices, monkey_args.seed, monkey_args.events,
           before, after)


def _handle_list(regex_string, devices):
    regex = None
    if not _NO_REGEX_FLAG == regex_string and regex_string.strip():
        regex = regex_string
    packages_dict = package_list(devices, regex)
    for device in packages_dict:
        _inform('installed packages on %s:', device)
        for package in packages_dict[device]:
            print package


def main():
    parser = _dumpey_args_parser()
    args = parser.parse_args()

    devices = args.devices if args.devices else attached_devices()

    if args.install:
        install(args.install, devices)
    if args.uninstall:
        uninstall(args.uninstall, devices)
    if args.apk:
        pull_apk(args.apk[0], args.apk[1], devices)
    if args.monkey:
        _handle_monkey(args.monkey[0], args.monkey[1:], devices)
    if args.heapdump:
        dump_heap(args.heapdump[0], args.heapdump[1], devices)
    if args.list:
        _handle_list(args.list, devices)


if __name__ == "__main__":
    # main()
    snapshots('4df1e80e3cd26ff3', '/Users/tadejslamic/Documents/reversed')