import unittest
import subprocess
import os

import mock

from dumpey import dumpey


@mock.patch('subprocess.Popen')
class DumpeyTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_adb(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        out = dumpey.adb(['dummy'])
        self.assertEqual(out, '')
        self.assert_popen_mock(popen_mock, 1, ['adb', 'dummy'])

    def test_adb_raise(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock(exit_value=1)
        self.assertRaises(Exception, dumpey.adb, ['dummy'])
        self.assert_popen_mock(popen_mock, 1, ['adb', 'dummy'])

    def test_decor_split(self, popen_mock):
        args = ' fst\n   snd\ntrd    \nfth'
        self.assertEqual(dumpey._decor_split(args),
                         ['fst', 'snd', 'trd', 'fth'])
        self.assertEqual(dumpey._decor_split(''), [])

    def test_decor_package(self, popen_mock):
        args = ' package:fst\n   package:snd\npackage:trd    \npackage:fth'
        self.assertEqual(dumpey._decor_package(args),
                         ['fst', 'snd', 'trd', 'fth'])
        self.assertEqual(dumpey._decor_package(''), [])

    def test_adb_decor(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock(out='fst\nsnd')
        out = dumpey.adb(['dummy'], decor=lambda l: l.split('\n'))
        self.assertEqual(out, ['fst', 'snd'])
        self.assert_popen_mock(popen_mock, 1, ['adb', 'dummy'])

    def test_adb_device(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        device = 'dummy_device'
        dumpey.adb(['dummy'], device)
        self.assert_popen_mock(popen_mock, 1, ['adb', '-s', device, 'dummy'])

    def test_attached_devices(self, popen_mock):
        raw_out = '''List of devices attached
                     4df1e80e3cd26ff3	device
                     3ab1e22a82d26eg3	device


                  '''
        popen_mock.return_value = self.create_popen_mock(out=raw_out)
        out = dumpey.attached_devices()
        self.assertEqual(out, ['4df1e80e3cd26ff3', '3ab1e22a82d26eg3'])
        self.assert_popen_mock(popen_mock, 1, ['adb', 'devices'])

    def test_attached_devices_raise(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        self.assertRaises(Exception, dumpey.attached_devices)
        self.assert_popen_mock(popen_mock, 1, ['adb', 'devices'])

    def test_attached_devices_raise_again(self, popen_mock):
        raw_out = '''List of devices attached


                  '''
        popen_mock.return_value = self.create_popen_mock(out=raw_out)
        self.assertRaises(Exception, dumpey.attached_devices)
        self.assert_popen_mock(popen_mock, 1, ['adb', 'devices'])

    def test_api_version(self, popen_mock):
        self.perform_api_version_test(popen_mock, '18')

    def test_api_version_converter(self, popen_mock):
        self.perform_api_version_test(popen_mock, 18, int)

    def perform_api_version_test(self, popen_mock, expected_out,
                                 converter=None):
        popen_mock.return_value = self.create_popen_mock(out='18\n\r\t')
        device = 'dummy_device'
        out = dumpey.api_version(device, converter)
        self.assertEqual(out, expected_out)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'getprop',
                                'ro.build.version.sdk'])

    @mock.patch('dumpey.dumpey.attached_devices')
    def test_install(self, attached_mock, popen_mock):
        self.perform_stall(dumpey.install, 'install', attached_mock, popen_mock)

    @mock.patch('dumpey.dumpey.attached_devices')
    def test_uninstall(self, attached_mock, popen_mock):
        self.perform_stall(dumpey.uninstall, 'uninstall', attached_mock,
                           popen_mock)

    def perform_stall(self, stall, stall_key, attached_mock, popen_mock):
        devices = ['dummy_fst', 'dummy_snd', 'dummy_trd']
        attached_mock.return_value = devices
        popen_mock.return_value = self.create_popen_mock()
        apk_path = 'dummy_apk_path'
        stall(apk_path)
        self.assertEqual(1, attached_mock.call_count)
        self.assert_popen_mock(popen_mock, 3,
                               ['adb', '-s', devices[0], stall_key, apk_path],
                               ['adb', '-s', devices[1], stall_key, apk_path],
                               ['adb', '-s', devices[2], stall_key, apk_path])

    def test_pull_apk_no_package(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        package = 'dummy.package'
        device = 'dummy_device'
        local_dir = 'local_dir'
        dumpey._pull_apk(package, device, local_dir)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'pm', 'path',
                                package])

    def test_pull_apk_multiple(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock(
            out='package:fst\npackage:snd')
        package = 'dummy.package'
        device = 'dummy_device'
        local_dir = 'local_dir'
        dumpey._pull_apk(package, device, local_dir)
        popen_mock.assert_called('1')
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'pm', 'path',
                                package])

    def test_pull_apk_ok(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock(out='package:fst\n')
        package = 'dummy.package'
        device = 'dummy_device'
        local_dir = 'local_dir'

        apk_name = 'fst'
        name = device + '_' + apk_name
        local_file = os.path.join(local_dir, name)

        dumpey._pull_apk(package, device, local_dir)
        self.assert_popen_mock(popen_mock, 2,
                               ['adb', '-s', device, 'shell', 'pm', 'path',
                                package],
                               ['adb', '-s', device, 'pull', '-p', apk_name,
                                local_file])

    @mock.patch('dumpey.dumpey.attached_devices')
    def test_monkey(self, attached_mock, popen_mock):
        devices = ['device_fst', 'device_snd']
        attached_mock.return_value = devices
        popen_mock.return_value = self.create_popen_mock()
        package = 'dummy.package'
        seed = 123
        before = mock.Mock()
        after = mock.Mock()
        dumpey.monkey(package, seed=123, before=before, after=after)
        self.assert_popen_mock(popen_mock, 2,
                               ['adb', '-s', devices[0], 'shell', 'monkey',
                                '-p', package, '-s', str(seed), str(1000)],
                               ['adb', '-s', devices[1], 'shell', 'monkey',
                                '-p', package, '-s', str(seed), str(1000)])
        self.assertEqual(2, before.call_count)
        self.assertEqual(2, after.call_count)

    def test_pid_ok(self, popen_mock):
        raw = 'root     31187 2    0     0    ffffffff 00000000 S dummy.package'
        popen_mock.return_value = self.create_popen_mock(out=raw)
        package = 'dummy.package'
        device = 'dummy_device'
        out = dumpey.pid(package, device)
        self.assertEqual(out, '31187')
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'ps'])

    def test_pid_retry(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        package = 'dummy.package'
        device = 'dummy_device'
        self.assertRaises(Exception, dumpey.pid, package, device)
        self.assert_popen_mock(popen_mock, 3,
                               ['adb', '-s', device, 'shell', 'monkey', '-p',
                                package, '-s', str(0), str(1)],
                               ['adb', '-s', device, 'shell', 'ps'])

    def test_remove_file(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        remote_path = 'dummy_file'
        device = 'dummy_device'
        dumpey.remove_file(remote_path, device)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'rm', '-f',
                                remote_path])

    def test_file_size_ok(self, popen_mock):
        raw = '-rw-r--r-- root   root        132 1970-01-01 01:00 dummy_file'
        popen_mock.return_value = self.create_popen_mock(out=raw)
        remote_path = 'dummy_file'
        device = 'dummy_device'
        out = dumpey.file_size(remote_path, device)
        self.assertEqual('132', out)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'ls', '-l',
                                remote_path])

    def test_file_size_raise(self, popen_mock):
        raw = 'dummy_file: No such file or directory'
        popen_mock.return_value = self.create_popen_mock(out=raw)
        remote_path = 'dummy_file'
        device = 'dummy_device'
        self.assertRaises(Exception, dumpey.file_size, remote_path, device)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'ls', '-l',
                                remote_path])

    def test_dump_heap_bad_version(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock(out='10\r')
        package = 'dummy.package'
        device = 'dummy_device'
        local_dir = 'dummy_dir'
        dumpey._dump_heap(package, device, local_dir)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'getprop',
                                'ro.build.version.sdk'])

    @mock.patch('dumpey.dumpey.api_version')
    @mock.patch('dumpey.dumpey.pid')
    def test_dump_heap(self, pid_mock, api_mock, popen_mock):
        pid_mock.return_value = '12345'
        api_mock.return_value = '18'

    def create_popen_mock(self, exit_value=0, out=None, err=None):
        if out is None:
            out = ''
        if err is None:
            err = ''
        popen_mock = mock.MagicMock()
        popen_mock.poll = mock.Mock(return_value=exit_value)
        popen_mock.communicate = mock.Mock(return_value=(out, err))
        return popen_mock

    def assert_popen_mock(self, popen_mock, times, *args):
        self.assertEquals(times, popen_mock.call_count)
        for arg in args:
            popen_mock.assert_any_call(arg, stdout=subprocess.PIPE)


    if __name__ == '__main__':
        unittest.main()