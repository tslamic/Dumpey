"""
Dumpey is a simple Python script that helps you

 - get any installed APK
 - stop and clear data of any package
 - do a converted memory dump
 - create a series of snapshots
 - run the monkey stress test AND extract memory dumps before and after it
 - install and uninstall multiple packages
 - list installed packages

on all attached devices, or just the ones you specify.
"""

__version__ = '0.8.3'

import subprocess
import argparse
import random
import time
import sys
import re
import os


def adb(args, device=None, decor=None):
    """
    Execute an adb command.

    Args:
        args: command as list.
        device: device serial as string.
        decor: function to process command output. Invoked with one param.
    Returns:
        the command output, altered by the decor function, if given.
    Raises:
        Exception: if the command return code is not 0.
    """
    head = ['adb', '-s', device] if device else ['adb']
    command = head + args
    output = _cmd(command)
    return decor(output) if decor else output


def api_version(device, decor=None):
    """
    Return the Android SDK version a given device is running on.

    Args:
        device: device serial as string.
        decor: function to process command output. Invoked with one param.
    Returns:
        the version number as a string, altered by the decor function,
        if given.
    """
    version = adb(['shell', 'getprop', 'ro.build.version.sdk'], device).strip()
    return decor(version) if decor else version


def attached_devices():
    """
    Return a list of currently attached devices.

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
    Stop and clear all data associated with a given package or the one found
    by regex. If regex matches multiple packages and force is True, data for
    each matching package is cleared.

    Args:
        package: package name as string.
        regex: string.
        devices: list of device serials.
        force: boolean.
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
    Create a converted heap dump for a given package or regex and download
    it to a local_dir. If local_dir is not given, the current working directory
    is used instead.

    If regex matches multiple packages and force is True, heap dumps will be
    made for each subsequent package.

    Args:
        package: package name as string.
        regex: string.
        devices: list of device serials.
        local_dir: local directory path as string.
        force: boolean.
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
    Return the size of a remote path on a given device.

    Args:
        remote_path: path to a file on a device as string.
        device: device serial as string.
    Raises:
        Exception: if remote_path is not found.
    """
    out = adb(['shell', 'ls', '-l', remote_path], device)
    if out.startswith(remote_path):
        raise Exception('%s not found' % remote_path)
    return _split_whitespace(out)[3]


def install(local_path=None, devices=None, recursive=False):
    """
    Install apk on given devices.

    If local path is a directory, it browses and installs any file ending
    with '.apk'. If recursive is True, each subdirectory it encounters is also
    checked.

    Args:
        local_path: path to a local file or directory as string.
        devices: device serial as string.
        recursive: boolean.
    Raises:
        Exception: if the local path does not exist.
    """
    if local_path is None:
        local_path = os.getcwd()
    elif not os.path.exists(local_path):
        raise Exception("%s does not exist" % local_path)
    if devices is None:
        devices = attached_devices()
    if os.path.isdir(local_path):
        _install_from_dir(local_path, devices, recursive)
    else:
        _install_from_file(local_path, devices)


# Default number of monkey events
_MONKEY_EVENTS = 1000

# Seed number for monkey will be a random number between the following
# MIN and MAX
_MONKEY_SEED_MIN = 10000
_MONKEY_SEED_MAX = 100000


def monkey(package=None, regex=None, devices=None, seed=None, events=None,
           before=None, after=None, log=True, force=False):
    """
    Run the monkey stress test.

    Args:
        package: package name as string.
        regex: string.
        devices: list of device serials.
        seed: int value for pseudo-random number generator.
        events: number of events to be injected as int.
        before: function to be executed before each monkey iteration
                starts. Receives two arguments: package name
                and device serial.
        after: function to be executed after each monkey iteration
               ends. Receives two arguments: package name
               and device serial.
        log: boolean.
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
        _package_iter(regex, devices, _monkey, force, seed, events, before,
                      after, log)


def package_list(devices=None, regex=None):
    """
    Return a dict of installed packages on given devices, filtered by
    the regex.

    Args:
        devices: list of device serials.
        regex: string.
    Returns:
        a dict of installed packages on each device, e.g.:
        {'device_1': ['package_1'], 'device_2': ['package_1', 'package_2']}
    """
    if devices is None:
        devices = attached_devices()
    compiled_regex = re.compile(regex) if regex else None
    return {device: _package_list(device, compiled_regex)
            for device in devices}


def pid(package, device, force_open=True):
    """
    Return the package process ID on a given device.

    If no PID is found and force_open is True, a package will be run and
    its PID retrieved.

    Args:
        package: package name as string.
        device: device serial as string.
        force_open: boolean.
    Raises:
        Exception: if force_open cannot open the given package, or if multiple
        PIDs are found.
    """
    out = adb(['shell', 'ps'], device, _decor_split)
    processes = [p.strip() for p in out if package in p]
    if not processes:
        if force_open:
            # The app might be installed, but is not running. Exec the monkey
            # with a single event, then re-query.
            _monkey(package, device, 0, 1, None, None, False)
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
        remote: path on a device to be copied as string.
        local: local path where remote file will be copied to as string.
        device device serial as string.
        show_progress: boolean.
    """
    command = ['pull', '-p', remote, local]
    if not show_progress:
        command.pop(1)
    adb(command, device)


def pull_apk(package=None, regex=None, devices=None, local_dir=None,
             force=False):
    """
    Downloads the package apk.

    If regex matches multiple packages and force is True, each package apk
    will be downloaded.

    Args:
        package: package name as string.
        regex: string.
        devices: list of device serials.
        local_dir: local directory as string.
        force: boolean.
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
    """
    Reboot the devices.

    Args:
        devices: list of device serials.
    """
    if devices is None:
        devices = attached_devices()
    for device in devices:
        adb(["reboot"], device)
        _inform("%s rebooted", device)


def remove_file(remote_path, device):
    """
    Remove the remote path from a device, if it exists.

    Args:
        remote_path: path on a device as string.
        device: device serial as string.
    """
    adb(['shell', 'rm', '-f', remote_path], device)


def snapshots(device=None, local_dir=None, multiple=False):
    """
    Take a snapshot of the current screen.

    If multiple is True, a new snapshot is taken each time ENTER is
    pressed. Snapshot is stored to a local_dir, or current working directory
    if local_dir is not given.

    Args:
        device: device serial as string.
        local_dir: local directory as string.
        multiple: boolean.
    Raises:
        Exception: if no device is given and there is more than one
                   attached device.
    """
    if device is None:
        devices = attached_devices()
        if len(devices) > 1:
            raise Exception('specify device serial')
        device = devices[0]
    if local_dir is None:
        local_dir = os.getcwd()
    if multiple:
        _inform("press enter to take a snapshot or [any key + enter] to exit")
        while sys.stdin.read(1) == "\n":
            _screenshot(device, local_dir)
    else:
        _screenshot(device, local_dir)


def uninstall(package=None, regex=None, devices=None, force=False):
    """
    Uninstall the package on all given devices.

    If force is True, any package matching the regex will be uninstalled.

    Args:
        package: package name as string.
        regex: string.
        devices: list of device serials.
        force: boolean.
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
    process = subprocess.Popen(args, stdout=subprocess.PIPE)
    output, err = process.communicate()
    returncode = process.poll()
    if returncode:
        raise Exception("failed to execute '%s', status=%d, err=%s"
                        % (_to_str(args, " "), returncode, err))
    return output


def _install_from_dir(local_dir, devices, recursive):
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


def _package_iter(regex, devices, func, force=False, *args):
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
                func(package, device, *args)
    return affected_devices


# No force option here - intuitively, it seems paths should always include a
# sole element. Since I'm not 100% sure, I'm leaving the checks in.
def _pull_apk(package, device, local_dir):
    paths = adb(['shell', 'pm', 'path', package], device, _decor_package)
    if not paths:
        _warn('path for package %s on %s not available', package, device)
    elif len(paths) > 1:
        _warn('multiple paths available on %s: %s', device, _to_str(paths))
    else:
        path = paths[0]
        name = _generate_name(device, os.path.basename(path), "apk")
        local = os.path.join(local_dir, name)
        pull(path, local, device)
        _inform('apk from %s downloaded to %s', device, local)


def _monkey(package, device, seed, events, before, after, log):
    if before is not None:
        before(package, device)
    if log:
        _inform('starting monkey (seed=%d, events=%d) on %s '
                'for package %s', seed, events, device, package)
    command = ['shell', 'monkey', '-p', package, '-s', str(seed), str(events)]
    adb(command, device)
    if after is not None:
        after(package, device)

# Path where a screenshot is temporarily saved on a device
_REMOTE_SCREENSHOT_PATH = '/sdcard/_dumpey_screenshot_tmp.png'


def _screenshot(device, local_dir):
    now = str(int(time.time()))
    name = _generate_name(device, now, "png")
    local_file = os.path.join(local_dir, name)
    remote = _REMOTE_SCREENSHOT_PATH
    adb(['shell', 'screencap', remote], device)
    pull(remote, local_file, device, show_progress=False)
    remove_file(remote, device)
    _inform("screenshot downloaded to %s", local_file)


# Path where a heap dump is temporarily saved on a device
_REMOTE_HEAP_DUMP_PATH = '/sdcard/_dumpey_hprof_tmp'


def _dump_heap(package, device, local_dir, append=None):
    api = api_version(device, int)
    if api < 11:
        _warn('heap dumps available on API > 10, device %s is %d', device, api)
        return

    pid_str = pid(package, device)
    remote = _REMOTE_HEAP_DUMP_PATH

    # Ensure the remote file does not exist, then do a dump.
    remove_file(remote, device)
    adb(['shell', 'am', 'dumpheap', pid_str, remote], device)

    # adb dumpheap command runs as a daemon.
    # We have to wait for it to finish - check the tmp file size
    # at timed intervals and stop when it's not changing anymore.
    #
    # This could be prettier.
    size = -1
    while True:
        time.sleep(1)
        temp = file_size(remote, device)
        if temp <= size:
            break
        size = temp

    # Create and pull the non-converted hprof dump.
    name = _generate_name(device, [package, append])
    local_file = os.path.join(local_dir, name + '.hprof')
    local_file_nonconv = local_file + '-nonconv'
    pull(remote, local_file_nonconv, device)

    # Convert heap dump if size is not 0, warn otherwise.
    if os.path.getsize(local_file_nonconv):
        _cmd(['hprof-conv', local_file_nonconv, local_file])
        os.remove(local_file_nonconv)
        remove_file(remote, device)
        _inform('converted hprof file available at %s', local_file)
    else:
        _warn("non-converted heap dump is empty, has '%s' crashed?", package)
        os.remove(local_file_nonconv)


def _package_list(device, compiled_regex):
    packages = adb(['shell', 'pm', 'list', 'packages'], device, _decor_package)
    return [p for p in packages if
            compiled_regex.search(p)] if compiled_regex else packages


def _clear_data(package, device):
    adb(["shell", "pm", "clear", package], device)
    _inform("cleared data for '%s' on device %s", package, device)


def _ensure_package_or_regex_given(package, regex):
    if not (package or regex):
        raise Exception("either package or regex must be given")


def _generate_name(device, item, extension=None):
    detail = _to_str(item, "_") if isinstance(item, list) else item
    string = _alphanum_str(device + "_" + detail)
    return "%s.%s" % (string, extension) if extension else string


def _decor_split(output, cleanup=None):
    splits = output.split('\n')
    return [cleanup(s) if cleanup else s.strip() for s in splits if s.strip()]


def _decor_package(output):
    return _decor_split(output, lambda l: l.strip().split('package:')[1])


def _split_whitespace(string):
    return re.sub(' +', ' ', string).split(' ')


def _alphanum_str(string):
    return re.sub(r'\W+', '_', string)


def _to_str(iterable, delimiter=', '):
    return delimiter.join(filter(None, iterable))


_SHELL_COLOR_LT_BLUE = '\033[94m'
_SHELL_COLOR_WARNING = '\033[91m'
_SHELL_COLOR_END = '\033[0m'


def _print(shell_color, string_format, *string_args):
    message = string_format % string_args
    print(shell_color + message + _SHELL_COLOR_END)


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
                                dest="devices",
                                help="device serials to run the command on")

    package_regex_parser = argparse.ArgumentParser(add_help=False)
    package_regex_parser.add_argument("-p", "--package", help="package name")
    package_regex_parser.add_argument("-r", "--regex", help="regex")
    package_regex_parser.add_argument("-f", "--force",
                                      action='store_true',
                                      help="force command on all packages "
                                           "matching the regex")

    path_parser = argparse.ArgumentParser(add_help=False)
    path_parser.add_argument("-o", "--source", help="file or directory path",
                             dest="path")

    subparsers = parser.add_subparsers(title="dumpey commands", dest="sub",
                                       help="commands")

    i = subparsers.add_parser("i", parents=[devices_parser, path_parser],
                              help="install APKs from path")
    i.add_argument("-r", "--recursive", action='store_true', help="recursive",
                   default=False)

    subparsers.add_parser("u", parents=[devices_parser, package_regex_parser],
                          help="uninstall apps")
    subparsers.add_parser("a", parents=[devices_parser, package_regex_parser,
                                        path_parser], help="download APKs")
    subparsers.add_parser("c", parents=[devices_parser, package_regex_parser],
                          help="stop and clear package data")
    subparsers.add_parser("r", parents=[devices_parser], help="reboot devices")
    subparsers.add_parser("h", parents=[devices_parser, package_regex_parser,
                                        path_parser],
                          help="do a heap dump")

    l = subparsers.add_parser("l", parents=[devices_parser],
                              help="list installed packages")
    l.add_argument("-r", "--regex", help="regex")

    monkey_parser = subparsers.add_parser("m",
                                          parents=[devices_parser,
                                                   package_regex_parser,
                                                   path_parser],
                                          help="run the monkey")
    monkey_parser.add_argument('--seed', type=int, help="seed value")
    monkey_parser.add_argument('--events', type=int,
                               help="number of events")
    monkey_parser.add_argument('--dump', choices=['b', 'a', 'ba', 'ab'],
                               help="perform heap dumps before (b), after(a) "
                                    "or before and after the monkey (ab|ba)")

    s = subparsers.add_parser("s", parents=[path_parser],
                              help="do snapshots")
    s.add_argument("-d", "--device", help="device serial")
    s.add_argument("-m", "--multi", help="take multiple snapshots",
                   action='store_true')

    return parser


def _handle_monkey(args, devices):
    before = after = None
    dump = args.dump
    if dump:
        local_dir = args.path if args.path else os.getcwd()
        if 'b' in dump:
            before = lambda p, d: _dump_heap(p, d, local_dir, 'before')
        if 'a' in dump:
            after = lambda p, d: _dump_heap(p, d, local_dir, 'after')
    monkey(args.package, args.regex, devices, args.seed, args.events, before,
           after, True, args.force)


def _handle_list(regex, devices):
    packages_dict = package_list(devices, regex)
    for device in packages_dict:
        if regex:
            _inform("installed packages on %s for '%s':", device, regex)
        else:
            _inform("installed packages on %s:", device)
        for package in packages_dict[device]:
            print(package)


def _main():
    parser = _dumpey_args_parser()
    args = parser.parse_args()

    sub = args.sub
    try:
        if 'a' == sub:
            pull_apk(args.package, args.regex, args.devices, args.path,
                     args.force)
        elif 'c' == sub:
            clear_data(args.package, args.regex, args.devices, args.force)
        elif 'h' == sub:
            dump_heap(args.package, args.regex, args.devices, args.path,
                      args.force)
        elif 'i' == sub:
            install(args.path, args.devices, args.recursive)
        elif 'r' == sub:
            reboot(args.devices)
        elif 'l' == sub:
            _handle_list(args.regex, args.devices)
        elif 'm' == sub:
            _handle_monkey(args, args.devices)
        elif 's' == sub:
            snapshots(args.device, args.path, args.multi)
        elif 'u' == sub:
            uninstall(args.package, args.regex, args.devices, args.force)
    except Exception as e:
        print(str(e))


if __name__ == "__main__":
    _main()
