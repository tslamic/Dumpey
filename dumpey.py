"""
Dumpey
"""

__version__ = '1.0.0'

import os
import re
import time
import subprocess
import argparse
from random import randint


_MONKEY_SEED_MIN = 1000
_MONKEY_SEED_MAX = 10000
_MONKEY_EVENTS = 1000

_REMOTE_HEAP_DUMP_PATH = '/sdcard/_dumpey_hprof_tmp'
_NO_REGEX_FLAG = '__no__regex__'

_SHELL_COLOR_LT_BLUE = '\033[94m'
_SHELL_COLOR_WARNING = '\033[93m'
_SHELL_COLOR_END = '\033[0m'


class Dumpey(object):
    """
    Dumpey class description
    """

    @staticmethod
    def adb(args, device=None, decor=None):
        """
        Executes an adb command.
        """
        head = ['adb', '-s', device] if device else ['adb']
        command = head + args
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        output, err = process.communicate()
        exit_val = process.poll()
        if exit_val:
            raise Exception('failed to execute "%s", status=%d, err=%s'
                            % (_to_str(command, ' '), exit_val, err))
        return decor(output) if decor else output

    def attached_devices(self):
        """
        Returns a list of currently attached devices, or raises an exception
        if none are available.
        """
        device_list = self.adb(['devices'], decor=_decor_split)[1:]
        devices = [d.split('\tdevice')[0] for d in device_list if d]
        if not devices:
            raise Exception('no devices attached')
        return devices

    def api_version(self, device, converter=None):
        """
        Returns the Android SDK version a given device is running on.
        """
        version = self.adb(['shell', 'getprop', 'ro.build.version.sdk'],
                           device).strip()
        return converter(version) if converter else version

    def install(self, apk_path, devices=None):
        """
        Installs the apk on all given devices.
        """
        if devices is None:
            devices = self.attached_devices()
        for device in devices:
            self.adb(['install', apk_path], device)
            _inform('%s installed on %s', apk_path, device)

    def uninstall(self, package, devices=None):
        """
        Uninstalls the package on all given devices.
        """
        if devices is None:
            devices = self.attached_devices()
        for device in devices:
            self.adb(['uninstall', package], device)
            _inform('%s uninstalled from %s', package, device)

    def pull_apk(self, package, devices=None, local_dir=None):
        """
        Downloads the apk of a specific package.
        """
        if devices is None:
            devices = self.attached_devices()
        if local_dir is None:
            local_dir = os.getcwd()
        for device in devices:
            self._pull_apk(package, device, local_dir)

    def _pull_apk(self, package, device, local_dir):
        paths = self.adb(['shell', 'pm', 'path', package], device,
                         _decor_package)
        if not paths:
            _warn('path for package %s on %s not available', package, device)
        elif len(paths) > 1:
            _warn('multiple paths available on %s: %s', device, _to_str(paths))
        else:
            path = paths[0]
            name = _alphanum_str(device) + '_' + os.path.basename(path)
            local_file = os.path.join(local_dir, name)
            self.adb(['pull', '-p', path, local_file], device)
            _inform('apk from %s downloaded to %s', device, local_file)

    def monkey(self, package, devices=None, seed=None, events=None,
               before=None, after=None, log=True):
        """
        Runs the monkey stress test.
        """
        if devices is None:
            devices = self.attached_devices()
        if seed is None:
            seed = randint(_MONKEY_SEED_MIN, _MONKEY_SEED_MAX)
        if events is None:
            events = _MONKEY_EVENTS
        for device in devices:
            if before:
                before(package, device)
            if log:
                _inform('starting monkey (seed=%d, events=%d) on %s '
                        'for package %s', seed, events, device, package)
            self.adb(['shell', 'monkey', '-p', package, '-s', str(seed),
                      str(events)], device)
            if after:
                after(package, device)

    def dump_heap(self, package, devices=None, local_dir=None):
        """
        Creates and downloads a heap dump of a given package.
        """
        if devices is None:
            devices = self.attached_devices()
        for device in devices:
            self._dump_heap(package, device, local_dir)

    def _dump_heap(self, package, device, local_dir=None, append=None):
        api = self.api_version(device, converter=int)
        if api < 11:
            _warn('heap dumps are only available on API > 10, device %s is %d',
                  device, api)
            return

        pid_str = self.pid(package, device)
        remote = _REMOTE_HEAP_DUMP_PATH

        self.remove_file(remote, device)
        self.adb(['shell', 'am', 'dumpheap', pid_str, remote], device)

        # dumpheap shell command runs as a daemon.
        # We have to wait for it to finish, so check the tmp file size
        # at timed intervals and stop when it's not changing anymore.
        # TODO: maybe this can be done better
        size = -1
        while True:
            time.sleep(.500)
            temp = self.file_size(remote, device)
            if temp <= size:
                break
            size = temp

        name = _alphanum_str(device) + '_' + _alphanum_str(package)
        if append:
            # name += '_' + append
            name = '%s_%s' % (name, append)
        if local_dir is None:
            local_dir = os.getcwd()
        local_file = os.path.join(local_dir, name + '.hprof')
        local_file_nonconv = local_file + '-nonconv'

        self.adb(['pull', '-p', remote, local_file_nonconv], device)
        subprocess.check_call(['hprof-conv', local_file_nonconv, local_file])
        os.remove(local_file_nonconv)
        self.remove_file(remote, device)
        _inform('converted hprof file available at %s', local_file)

    def package_list(self, devices=None, regex=None):
        """
        Returns a dict with install packages on each device, filtered by
        the regex, if given.
        """
        if devices is None:
            devices = self.attached_devices()
        compiled = re.compile(regex) if regex else None
        return {device: self._package_list(device, compiled)
                for device in devices}

    def _package_list(self, device, regex):
        packages = self.adb(['shell', 'pm', 'list', 'packages'], device,
                            _decor_package)
        return [p for p in packages if regex.search(p)] if regex else packages

    def pid(self, package, device, retry=True):
        """
        Returns the package process ID on a specified device.
        """
        out = self.adb(['shell', 'ps'], device, _decor_split)
        processes = [p.strip() for p in out if package in p]
        if not processes:
            # The app might be installed, but is not running. Run the monkey
            # with a single event, then re-query.
            if retry:
                self.monkey(package, [device], seed=0, events=1, log=False)
                return self.pid(package, device, retry=False)
            raise Exception('no process on %s found for %s, is your app '
                            'installed?' % (device, package))
        if len(processes) > 1:
            raise Exception('Multiple processes for %s: %s.'
                            % package, _to_str(processes))
        return _split_whitespace(processes[0])[1]

    def file_size(self, file_path, device):
        """
        Returns the size of a file on a given device.
        """
        out = self.adb(['shell', 'ls', '-l', file_path], device)
        if out.startswith(file_path):
            raise Exception('%s not found' % file_path)
        return _split_whitespace(out)[3]

    def remove_file(self, remote_path, device):
        """
        Removes the remote path from a device, if it exists.
        """
        self.adb(['shell', 'rm', '-f', remote_path], device)


###########
# Helpers #
###########

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


def _create_args_parser():
    parser = argparse.ArgumentParser(
        description=''' Dumpey helps you download any installed APK from a
                        device, download a converted memory dump, run the monkey
                        with memory dumps before and after it and install and
                        uninstall APKs from multiple attached devices.''')
    parser.add_argument('-i', '--install',
                        metavar='APK',
                        help='installs the apk')
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


def _handle_monkey(dumpey, package, args, devices):
    if not args:
        dumpey.monkey(package, devices)
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
            before = lambda p, d: dumpey.dump_heap(p, [d], local_dir, 'before')
        if 'a' in monkey_args.heap:
            after = lambda p, d: dumpey.dump_heap(p, [d], local_dir, 'after')
    dumpey.monkey(package, devices, monkey_args.seed, monkey_args.events,
                  before, after)


def _handle_list(dumpey, regex_string, devices):
    regex = None
    if not _NO_REGEX_FLAG == regex_string and regex_string.strip():
        regex = re.compile(regex_string)
    packages_dict = dumpey.package_list(devices, regex)
    for device in packages_dict:
        _inform('installed packages on %s:', device)
        for package in packages_dict[device]:
            print package


def main():
    parser = _create_args_parser()
    args = parser.parse_args()

    dumpey = Dumpey()
    devices = args.devices if args.devices else dumpey.attached_devices()

    if args.install:
        dumpey.install(args.install, devices)
    if args.uninstall:
        dumpey.uninstall(args.uninstall, devices)
    if args.apk:
        dumpey.pull_apk(args.apk[0], args.apk[1], devices)
    if args.monkey:
        _handle_monkey(dumpey, args.monkey[0], args.monkey[1:], devices)
    if args.heapdump:
        dumpey.dump_heap(args.heapdump[0], args.heapdump[1], devices)
    if args.list:
        _handle_list(dumpey, args.list, devices)


if __name__ == "__main__":
    main()