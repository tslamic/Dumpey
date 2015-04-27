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


#
# Public API
#


def adb(args, device=None, decor=None):
    """
    Executes an adb command.

    Args:
        args:   Command as list.
        device: Device serial as string.
        decor:  Function to process command output.
                Will be called with one argument - the command raw output.

    Returns:
        The command output, altered by the decor function, if given.

    Raises:
        Exception: if the command return code is not 0.
    """
    head = ['adb', '-s', device] if device else ['adb']
    command = head + args
    output = _cmd(command)
    return decor(output) if decor else output


def api_version(device, decor=None):
    """
    Returns the Android SDK version a given device is running on.

    Args:
        device: Device serial as string.
        decor:  Function to process command output.
                Will be called with one argument - the command raw output.

    Returns:
        The version number as a string, altered by the decor function,
        if given.
    """
    version = adb(['shell', 'getprop', 'ro.build.version.sdk'], device).strip()
    return decor(version) if decor else version


def attached_devices():
    """
    Returns a list of currently attached devices.

    Raises:
        Exception: if there are no devices in "device" state.
    """
    raw_list = adb(['devices'], decor=_decor_split)[1:]
    delimiter = "\tdevice"
    devices = [d.split(delimiter)[0] for d in raw_list if delimiter in d]
    if not devices:
        raise Exception("no devices in 'device' state")
    return devices


def clear_data(package=None, regex=None, devices=None, force=False):
    """
    Clears all data associated with a given package.

    If multiple packages are found via regex search and force is True,
    all data associated with each package is cleared. Ignored if regex is
    not given.

    Args:
        package:    Package name as string.
        regex:      Regex filter as string.
        devices:    List of device serials.
        force:      Boolean value.

    Raises:
        Exception: if neither package nor regex is given.
    """
    _ensure_package_or_regex_given(package, regex)
    if devices is None:
        devices = attached_devices()
    if package is not None:
        for device in devices:
            _clear_data(package, device)
    else:
        _package_iter(regex, devices, _clear_data, force)


def dump_heap(package=None, regex=None, devices=None, local_dir=None,
              force=False):
    """
    Creates a heap dump, then downloads and converts it to a given local
    directory. If not given, the current working directory will be used
    instead.

    Args:
        package:    Package name as string.
        regex:      Regex filter as string.
        devices:    List of device serials.
        local_dir:  Local directory path as string.
        force:      Boolean value.

    Raises:
        Exception: if neither package nor regex is given.
    """
    _ensure_package_or_regex_given(package, regex)
    if devices is None:
        devices = attached_devices()
    if local_dir is None:
        local_dir = os.getcwd()
    if package is not None:
        for device in devices:
            _dump_heap(package, device, local_dir)
    else:
        _package_iter(regex, devices, _dump_heap, force, local_dir)


def file_size(remote_path, device):
    """
    Returns the file size on a given device.

    Args:
        remote_path:    Path to a file on a device as string.
        device:         Device serial as string.

    Raises:
        Exception: if the remote_path is not found.
    """
    out = adb(['shell', 'ls', '-l', remote_path], device)
    if out.startswith(remote_path):
        raise Exception('%s not found' % remote_path)
    return _split_whitespace(out)[3]


def install(local_path=None, devices=None, recursive=False):
    """
    Installs the apk on all given devices.

    If local path is a directory, it browses through and installs any file
    ending with '.apk'. If recursive is True, it visits each subsequent
    directory and applies the same logic.

    Args:
        local_path: Path to a local file or directory as string.
        devices:    Device serial as string.
        recursive:  Boolean value.

    Raises:
        Exception: if the local path does not exist.
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


_MONKEY_EVENTS = 1000
_MONKEY_SEED_MIN = 10000
_MONKEY_SEED_MAX = 100000


def monkey(package=None, regex=None, devices=None, seed=None, events=None,
           before=None, after=None, log=True, force=False):
    """
    Runs the monkey stress test.

    Args:
        package:    Package name as string.
        regex:      Regex filter as string.
        devices:    List of device serials.
        seed:       Int value for pseudo-random number generator.
        events:     Number of events to be injected as int.
        before:     Function to be executed before each monkey iteration
                    starts. Receives two arguments: package name
                    and device serial.
        after:      Function to be executed after each monkey iteration
                    ends. Receives two arguments: package name
                    and device serial.
        log:        Boolean value determining if monkey status should be
                    printed.

    Raises:
        Exception: if neither package nor regex is given.
    """
    _ensure_package_or_regex_given(package, regex)
    if devices is None:
        devices = attached_devices()
    if seed is None:
        seed = random.randint(_MONKEY_SEED_MIN, _MONKEY_SEED_MAX)
    if events is None:
        events = _MONKEY_EVENTS
    if package is not None:
        for device in devices:
            _monkey(package, device, seed, events, before, after, log)
    else:
        _package_iter(regex, devices, _monkey, force, seed, events,
                      before, after, log)


def _monkey(package, device, seed, events, before, after, log):
    if before:
        before(package, device)
    if log:
        _inform('starting monkey (seed=%d, events=%d) on %s '
                'for package %s', seed, events, device, package)
    s = str(seed)
    e = str(events)
    adb(['shell', 'monkey', '-p', package, '-s', s, e], device)
    if after:
        after(package, device)


def package_list(devices=None, regex=None):
    """
    Returns a list of installed packages on given devices, filtered by
    the regex, if not None.

    Args:
        devices:    List of device serials.
        regex:      Regex filter as string.

    Returns:
        A dict of installed packages on each subsequent device, e.g.:
        {'device_1': ['package_1'], 'device_2': ['package_1', 'package_2']}
    """
    if devices is None:
        devices = attached_devices()
    compiled_regex = re.compile(regex) if regex else None
    return {device: _package_list(device, compiled_regex)
            for device in devices}


def pid(package, device, force_open=True):
    """
    Returns the package process ID on a specific device.

    If no PID is found and force_open is True, a package will be run and
    its PID retrieved.

    Args:
        package:    Package name as string.
        device:     Device serial as string.
        force_open: Boolean value.

    Raises:
        Exception:  if force_open cannot open the given package, or if multiple
                    PIDs are found.
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
        raise Exception('multiple processes for %s: %s.' % package,
                        _to_str(processes))
    return _split_whitespace(processes[0])[1]


def pull(remote, local, device, show_progress=True):
    """
    Copies files from a device.

    Args:
        remote:         Path on a device to be copied, as string.
        local:          Local path where remote file will be copied to,
                        as string.
        device:         Device serial as string.
        show_progress:  Boolean value.
    """
    command = ['pull', '-p', remote, local]
    if not show_progress:
        command.pop(1)
    adb(command, device)


def pull_apk(package=None, regex=None, devices=None, local_dir=None,
             force=False):
    """
    Downloads the apk of a specific package.
    """
    _ensure_package_or_regex_given(package, regex)
    if devices is None:
        devices = attached_devices()
    if local_dir is None:
        local_dir = os.getcwd()
    if package is not None:
        for device in devices:
            _pull_apk(package, device, local_dir)
    else:
        _package_iter(regex, devices, _pull_apk, force, local_dir)


def reboot(devices):
    if devices is None:
        devices = attached_devices()
    for device in devices:
        adb(["shell", "reboot"], device)


def remove_file(remote_path, device):
    """
    Removes the remote path from a device, if it exists.
    """
    adb(['shell', 'rm', '-f', remote_path], device)


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


def uninstall(package=None, regex=None, devices=None, force=False):
    """
    Uninstalls the package on all given devices.
    Either package or regex must be given.
    If force is True, any package fitting the regex will be uninstalled.
    If both package and regex are given, only package is considered.
    """
    _ensure_package_or_regex_given(package, regex)
    if devices is None:
        devices = attached_devices()
    if package is not None:
        for device in devices:
            _uninstall_package(package, device)
    else:
        _package_iter(regex, devices, _uninstall_package, force)


#
# Helpers
#


def _cmd(args):
    """
    Executes a shell command.
    """
    process = subprocess.Popen(args, stdout=subprocess.PIPE)
    output, err = process.communicate()
    returncode = process.poll()
    if returncode:
        raise Exception("failed to execute '%s', status=%d, err=%s"
                        % (_to_str(args, " "), returncode, err))
    return output


def _install_from_dir(local_dir, devices, recursive):
    _inform("install invoked on %s", local_dir)
    for item in os.listdir(local_dir):
        item_path = os.path.join(local_dir, item)
        if item.endswith(".apk"):
            _install_from_file(item_path, devices)
        elif recursive and os.path.isdir(item_path):
            _install_from_dir(item_path, devices, recursive)


def _install_from_file(local_file, devices):
    for device in devices:
        adb(['install', local_file], device)
        _inform('%s installed on %s', local_file, device)


def _uninstall_package(package, device):
    adb(['uninstall', package], device)
    _inform('%s uninstalled from %s', package, device)


def _package_iter(regex, devices, f, force=False, *args):
    affected_devices = []
    compiled_regex = re.compile(regex)
    for device in devices:
        packages = _package_list(device, compiled_regex)
        if not packages:
            _warn("nothing found for regex '%s' on %s", regex, device)
        elif len(packages) > 1 and not force:
            _warn("multiple apps found for regex '%s' on %s: %s", regex,
                  device, _to_str(packages))
        else:
            affected_devices.append(device)
            for package in packages:
                f(package, device, *args)
    return affected_devices


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


_REMOTE_HEAP_DUMP_PATH = '/sdcard/_dumpey_hprof_tmp'


def _dump_heap(package, device, local_dir, append=None):
    api = api_version(device, int)
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


def _package_list(device, compiled_regex):
    packages = adb(['shell', 'pm', 'list', 'packages'], device, _decor_package)
    return [p for p in packages if
            compiled_regex.search(p)] if compiled_regex else packages


def _clear_data(package, device):
    adb(["shell", "pm", "clear", package], device)


def _ensure_package_or_regex_given(package, regex):
    if not (package or regex):
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


_SHELL_COLOR_LT_BLUE = '\033[94m'
_SHELL_COLOR_WARNING = '\033[91m'
_SHELL_COLOR_END = '\033[0m'


def _print(shell_color, string_format, *string_args):
    message = string_format % string_args
    print shell_color + message + _SHELL_COLOR_END


def _warn(string_format, *string_args):
    _print(_SHELL_COLOR_WARNING, string_format, *string_args)


def _inform(string_format, *string_args):
    _print(_SHELL_COLOR_LT_BLUE, string_format, *string_args)


def _add_parser_pull_apk(sub, devices_parser):
    p = sub.add_parser("a", parents=[devices_parser], help="download APKs")
    p.add_argument("-p", "--package", help="package name")
    p.add_argument("-r", "--regex", help="regex string")
    p.add_argument("-f", "--force",
                   help="force uninstall on all filtered packages")


def _dumpey_args_parser():
    parser = argparse.ArgumentParser(
        description="Dumpey, an Android Debug Bridge utility tool."
    )
    devices_parser = argparse.ArgumentParser(add_help=False)
    devices_parser.add_argument("-s",
                                "--serials",
                                nargs="+",
                                metavar="SERIAL",
                                dest="devices",
                                help="Device serials to run the command on")
    package_regex_parser = argparse.ArgumentParser(add_help=False)
    package_regex_parser.add_argument("-p", "--package", help="package name",
                                      dest="pacreg")
    package_regex_parser.add_argument("-f", "--force",
                                      help="force op on all filtered packages")
    path_parser = argparse.ArgumentParser(add_help=False)
    path_parser.add_argument("-o", "--source", help="file or directory path",
                             dest="path")

    subparsers = parser.add_subparsers(title="Available commands",
                                       dest="sub",
                                       help="options provided by dumpey")

    i = subparsers.add_parser("i", parents=[devices_parser, path_parser],
                              help="install APKs from a given path")
    i.add_argument("-r", "--recursive", action='store_true', help="recursive",
                   default=False)

    subparsers.add_parser("u", parents=[devices_parser, package_regex_parser],
                          help="uninstall apps")
    subparsers.add_parser("a", parents=[devices_parser], help="download APKs")
    subparsers.add_parser("c", parents=[devices_parser, package_regex_parser],
                          help="clears package data")
    subparsers.add_parser("k", parents=[devices_parser], help="reboot devices")
    subparsers.add_parser("e", parents=[devices_parser, package_regex_parser,
                                        path_parser],
                          help="performs a heap dump")

    l = subparsers.add_parser("l", parents=[devices_parser],
                              help="lists installed packages")
    l.add_argument("-r", "--regex", help="regex string")

    monkey_parser = subparsers.add_parser("m",
                                          parents=[devices_parser,
                                                   package_regex_parser,
                                                   path_parser],
                                          help="runs the monkey")
    monkey_parser.add_argument('--seed', type=int, help="seed value")
    monkey_parser.add_argument('--events', type=int,
                               help="number of events")
    monkey_parser.add_argument('--heap', choices=['b', 'a', 'ba', 'ab'],
                               help="perform heap dumps before (b), after(a) "
                                    "or before and after the monkey (ab|ba)")

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


def _handle_list(regex, devices):
    packages_dict = package_list(devices, regex)
    for device in packages_dict:
        _inform('installed packages on %s:', device)
        for package in packages_dict[device]:
            print package


def main():
    parser = _dumpey_args_parser()
    args = vars(parser.parse_args())

    print args, os.getcwd()

    cmd = args.get('sub')
    devices = args.get('devices')

    {'a': lambda: pull_apk(args.p, args.r, devices, args.o, args.f),
     'c': lambda: clear_data(args.p, args.r, devices, args.f),
     'e': lambda: dump_heap(args.p, args.r, devices, args.o, args.f),
     'i': lambda: install(args.get('source'), devices, args.get('regex')),
     'k': lambda: reboot(devices),
     'l': lambda: _handle_list(args.get('regex'), devices),
     'm': lambda l: None,
     'u': lambda: uninstall(args.p, args.r, devices, args.f),
     }.get(cmd)()


if __name__ == "__main__":
    main()