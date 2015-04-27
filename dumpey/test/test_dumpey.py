import unittest
import subprocess

import mock

from dumpey import dumpey


@mock.patch('subprocess.Popen', autospec=True)
class DumpeyTest(unittest.TestCase):
    DUMMY = "dummy"
    DUMMY_LIST = [DUMMY]

    DEVICE_1 = "dummy_device_1"
    DEVICE_2 = "dummy_device_2"
    DEVICE_3 = "dummy_device_3"
    DEVICES = [DEVICE_1, DEVICE_2, DEVICE_3]

    PACKAGE_1 = "com.dummy.package.fst"
    PACKAGE_2 = "com.dummy.package.snd"
    PACKAGE_3 = "com.dummy.package.trd"
    PACKAGES = [PACKAGE_1, PACKAGE_2, PACKAGE_3]

    def test_adb(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock(out=DumpeyTest.DUMMY)
        out = dumpey.adb(DumpeyTest.DUMMY_LIST)
        self.assertEqual(out, DumpeyTest.DUMMY)
        self.assert_popen_mock(popen_mock, 1, ['adb', DumpeyTest.DUMMY])

    def test_adb_raise(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock(exit_value=1)
        self.assertRaises(Exception, dumpey.adb, DumpeyTest.DUMMY_LIST)
        self.assert_popen_mock(popen_mock, 1, ['adb', DumpeyTest.DUMMY])

    def test_adb_decor(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        decor = lambda l: DumpeyTest.DUMMY
        out = dumpey.adb(DumpeyTest.DUMMY_LIST, decor=decor)
        self.assertEqual(out, DumpeyTest.DUMMY)
        self.assert_popen_mock(popen_mock, 1, ['adb', DumpeyTest.DUMMY])

    def test_api_version(self, popen_mock):
        self.perform_api_version_test(popen_mock, '18')

    def test_api_version_decor_fst(self, popen_mock):
        self.perform_api_version_test(popen_mock, 18, int)

    def test_api_version_decor_snd(self, popen_mock):
        decor = lambda l: DumpeyTest.DUMMY
        self.perform_api_version_test(popen_mock, DumpeyTest.DUMMY, decor)

    def perform_api_version_test(self, popen_mock, expected_out, decor=None):
        raw = '18\n\r\t'
        popen_mock.return_value = self.create_popen_mock(out=raw)
        device = DumpeyTest.DEVICE_1
        out = dumpey.api_version(device, decor)
        self.assertEqual(out, expected_out)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'getprop',
                                'ro.build.version.sdk'])

    def test_attached_devices_none(self, popen_mock):
        raw = "List of devices attached\n\n"
        popen_mock.return_value = self.create_popen_mock(out=raw)
        self.assertRaises(Exception, dumpey.attached_devices)

    def test_attached_devices_one_offline(self, popen_mock):
        raw = "List of devices attached\n%s\toffline\n" % DumpeyTest.DEVICE_1
        popen_mock.return_value = self.create_popen_mock(out=raw)
        self.assertRaises(Exception, dumpey.attached_devices)

    def test_attached_devices_one_not_attached(self, popen_mock):
        raw = "List of devices attached\n%s\tno device\n" % DumpeyTest.DEVICE_1
        popen_mock.return_value = self.create_popen_mock(out=raw)
        self.assertRaises(Exception, dumpey.attached_devices)

    def test_attached_devices_one_attached(self, popen_mock):
        raw = "List of devices attached\n%s\tdevice\n" % DumpeyTest.DEVICE_1
        popen_mock.return_value = self.create_popen_mock(out=raw)
        out = dumpey.attached_devices()
        self.assertEquals([DumpeyTest.DEVICE_1], out)
        self.assert_popen_mock(popen_mock, 1, ['adb', 'devices'])

    def test_attached_devices(self, popen_mock):
        raw = "List of devices attached\n%s\tdevice\n%s\tdevice\n%s\tdevice\n" \
              % (DumpeyTest.DEVICE_1, DumpeyTest.DEVICE_2, DumpeyTest.DEVICE_3)
        popen_mock.return_value = self.create_popen_mock(out=raw)
        out = dumpey.attached_devices()
        self.assertEquals(DumpeyTest.DEVICES, out)
        self.assert_popen_mock(popen_mock, 1, ['adb', 'devices'])

    @mock.patch('dumpey.dumpey._package_list', autospec=True)
    @mock.patch('re.compile', autospec=True)
    def test_package_iter_none(self, compile_mock, package_list_mock,
                               popen_mock):
        package_list_mock.return_value = []
        f = mock.Mock()
        out = dumpey._package_iter("", [], f)
        self.assertEquals([], out)
        self.assertEquals(1, compile_mock.call_count)
        self.assertEquals(0, package_list_mock.call_count)
        self.assertEquals(0, popen_mock.call_count)
        self.assertEquals(0, f.call_count)

    @mock.patch('dumpey.dumpey._package_list', autospec=True)
    @mock.patch('re.compile', autospec=True)
    def test_package_iter_one(self, compile_mock, package_list_mock,
                              popen_mock):
        self.package_iter(compile_mock, package_list_mock, popen_mock,
                          [DumpeyTest.PACKAGE_1], DumpeyTest.DEVICES,
                          DumpeyTest.DEVICES, len(DumpeyTest.DEVICES))

    @mock.patch('dumpey.dumpey._package_list', autospec=True)
    @mock.patch('re.compile', autospec=True)
    def test_package_iter_many(self, compile_mock, package_list_mock,
                               popen_mock):
        self.package_iter(compile_mock, package_list_mock, popen_mock,
                          DumpeyTest.PACKAGES, DumpeyTest.DEVICES, [], 0)

    @mock.patch('dumpey.dumpey._package_list', autospec=True)
    @mock.patch('re.compile', autospec=True)
    def test_package_iter_many(self, compile_mock, package_list_mock,
                               popen_mock):
        packages_dict = {
            DumpeyTest.DEVICE_1: [DumpeyTest.PACKAGE_1],
            DumpeyTest.DEVICE_2: [DumpeyTest.PACKAGE_1, DumpeyTest.PACKAGE_2],
            DumpeyTest.DEVICE_3: DumpeyTest.PACKAGES
        }
        packages = lambda d, r: packages_dict.get(d)
        package_list_mock.side_effect = packages
        f = mock.Mock()
        out = dumpey._package_iter("", DumpeyTest.DEVICES, f)
        self.assertEquals([DumpeyTest.DEVICE_1], out)
        self.assertEquals(1, compile_mock.call_count)
        self.assertEquals(3, package_list_mock.call_count)
        self.assertEquals(1, f.call_count)
        self.assertEquals(0, popen_mock.call_count)

    def package_iter(self, compile_mock, package_list_mock, popen_mock,
                     packages, devices, expected, fcount):
        package_list_mock.return_value = packages
        f = mock.Mock()
        out = dumpey._package_iter("", devices, f)
        self.assertEquals(expected, out)
        self.assertEquals(1, compile_mock.call_count)
        self.assertEquals(len(devices), package_list_mock.call_count)
        self.assertEquals(fcount, f.call_count)
        self.assertEquals(0, popen_mock.call_count)

    def test_ensure_package_or_regex_given(self, popen_mock):
        self.assertRaises(Exception, dumpey._ensure_package_or_regex_given,
                          "", "")
        self.assertRaises(Exception, dumpey._ensure_package_or_regex_given,
                          None, None)
        self.assertRaises(Exception, dumpey._ensure_package_or_regex_given,
                          "", None)
        self.assertRaises(Exception, dumpey._ensure_package_or_regex_given,
                          None, "")
        exc = None
        try:
            dumpey._ensure_package_or_regex_given("ok", None)
            dumpey._ensure_package_or_regex_given(None, "ok")
            dumpey._ensure_package_or_regex_given("ok", "ok")
        except Exception as e:
            exc = e
        self.assertIsNone(exc)
        self.assertEquals(0, popen_mock.call_count)

    # TEST CLEAR DATA

    # TEST DUMP HEAP

    def test_split_whitespace(self, popen_mock):
        fst = "a b  c   d    e     f      g       h"
        snd = "a       b      c     d    e   f  g h"
        res = ["a", "b", "c", "d", "e", "f", "g", "h"]
        self.assertEquals(dumpey._split_whitespace(fst), res)
        self.assertEquals(dumpey._split_whitespace(snd), res)

    def test_file_size_exists(self, popen_mock):
        raw = "-rw-r--r-- root  root       611 1970-01-01 00:00 dummy"
        popen_mock.return_value = self.create_popen_mock(out=raw)
        remote = DumpeyTest.DUMMY
        out = dumpey.file_size(remote, DumpeyTest.DEVICE_1)
        self.assertEquals("611", out)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', DumpeyTest.DEVICE_1, 'shell',
                                'ls', '-l', remote])

    def test_file_size_fails(self, popen_mock):
        raw = "dummy: No such file or directory"
        popen_mock.return_value = self.create_popen_mock(out=raw)
        remote = DumpeyTest.DUMMY
        self.assertRaises(Exception, dumpey.file_size, remote,
                          DumpeyTest.DEVICE_1)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', DumpeyTest.DEVICE_1, 'shell',
                                'ls', '-l', remote])

    # TEST INSTALL

    # TEST MONKEY

    # TEST PACKAGE LIST

    # TEST PID

    def test_pull_progress(self, popen_mock):
        self.exec_pull(popen_mock, True)

    def test_pull_no_progress(self, popen_mock):
        self.exec_pull(popen_mock, False)

    def exec_pull(self, popen_mock, show_progress):
        popen_mock.return_value = self.create_popen_mock()
        remote = DumpeyTest.DUMMY
        local = DumpeyTest.DUMMY + "_local"
        device = DumpeyTest.DEVICE_1
        dumpey.pull(remote, local, device, show_progress=show_progress)
        if show_progress:
            self.assert_popen_mock(popen_mock, 1,
                                   ['adb', '-s', device, 'pull', '-p',
                                    remote, local])
        else:
            self.assert_popen_mock(popen_mock, 1,
                                   ['adb', '-s', device, 'pull',
                                    remote, local])

    # TEST PULL APK

    def test_reboot(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        devices = DumpeyTest.DEVICES
        dumpey.reboot(devices)
        self.assert_popen_mock(popen_mock, 3,
                               ['adb', '-s', DumpeyTest.DEVICE_1, 'shell',
                                'reboot'],
                               ['adb', '-s', DumpeyTest.DEVICE_2, 'shell',
                                'reboot'],
                               ['adb', '-s', DumpeyTest.DEVICE_3, 'shell',
                                'reboot'])

    def test_remove_file(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        remote = DumpeyTest.DUMMY
        device = DumpeyTest.DEVICE_1
        dumpey.remove_file(remote, device)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'rm', '-f',
                                remote])

    # TEST SINGLE SNAPSHOT

    # TEST SNAPSHOTS

    # TEST UNINSTALL

    # TEST _CMD

    # TEST INSTALL_FROM_DIR

    # TEST INSTALL_FROM_FILE

    def test_uninstall_package(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        package = DumpeyTest.PACKAGE_1
        device = DumpeyTest.DEVICE_1
        dumpey._uninstall_package(package, device)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'uninstall', package])

    # TEST _PULL_APK

    # TEST _SNAPSHOT

    # TEST _DUMP_HEAP



    # def test_decor_split(self, popen_mock):
    # args = ' fst\n   snd\ntrd    \nfth'
    # self.assertEqual(dumpey._decor_split(args),
    # ['fst', 'snd', 'trd', 'fth'])
    # self.assertEqual(dumpey._decor_split(''), [])
    #
    # def test_decor_package(self, popen_mock):
    # args = ' package:fst\n   package:snd\npackage:trd    \npackage:fth'
    # self.assertEqual(dumpey._decor_package(args),
    # ['fst', 'snd', 'trd', 'fth'])
    # self.assertEqual(dumpey._decor_package(''), [])
    #
    # def test_adb_decor(self, popen_mock):
    # popen_mock.return_value = self.create_popen_mock(out='fst\nsnd')
    # out = dumpey.adb(['dummy'], decor=lambda l: l.split('\n'))
    # self.assertEqual(out, ['fst', 'snd'])
    # self.assert_popen_mock(popen_mock, 1, ['adb', 'dummy'])
    #
    # def test_adb_device(self, popen_mock):
    # popen_mock.return_value = self.create_popen_mock()


    # device = 'dummy_device'


    # dumpey.adb(['dummy'], device)
    # self.assert_popen_mock(popen_mock, 1, ['adb', '-s', device, 'dummy'])
    #
    # def test_attached_devices(self, popen_mock):
    # raw_out = '''List of devices attached
    # 4df1e80e3cd26ff3	device
    # 3ab1e22a82d26eg3	device
    #
    #
    # '''
    # popen_mock.return_value = self.create_popen_mock(out=raw_out)
    # out = dumpey.attached_devices()
    # self.assertEqual(out, ['4df1e80e3cd26ff3', '3ab1e22a82d26eg3'])
    # self.assert_popen_mock(popen_mock, 1, ['adb', 'devices'])
    #
    # def test_attached_devices_raise(self, popen_mock):
    # popen_mock.return_value = self.create_popen_mock()
    # self.assertRaises(Exception, dumpey.attached_devices)
    # self.assert_popen_mock(popen_mock, 1, ['adb', 'devices'])
    #
    # def test_attached_devices_raise_again(self, popen_mock):
    # raw_out = '''List of devices attached
    #
    #
    # '''
    # popen_mock.return_value = self.create_popen_mock(out=raw_out)
    # self.assertRaises(Exception, dumpey.attached_devices)
    # self.assert_popen_mock(popen_mock, 1, ['adb', 'devices'])
    #
    # def test_api_version(self, popen_mock):
    # self.perform_api_version_test(popen_mock, '18')
    #
    # def test_api_version_converter(self, popen_mock):
    # self.perform_api_version_test(popen_mock, 18, int)
    #
    # def perform_api_version_test(self, popen_mock, expected_out,
    # converter=None):
    # popen_mock.return_value = self.create_popen_mock(out='18\n\r\t')
    # device = 'dummy_device'
    # out = dumpey.api_version(device, converter)
    # self.assertEqual(out, expected_out)
    # self.assert_popen_mock(popen_mock, 1,
    # ['adb', '-s', device, 'shell', 'getprop',
    # 'ro.build.version.sdk'])
    #
    # @mock.patch('dumpey.dumpey.attached_devices')
    # def test_install(self, attached_mock, popen_mock):
    # self.perform_stall(dumpey.install, 'install', attached_mock,
    # popen_mock)
    #
    # @mock.patch('dumpey.dumpey.attached_devices')
    # def test_uninstall(self, attached_mock, popen_mock):
    # self.perform_stall(dumpey.uninstall, 'uninstall', attached_mock,
    # popen_mock)
    #
    # def perform_stall(self, stall, stall_key, attached_mock, popen_mock):
    # devices = ['dummy_fst', 'dummy_snd', 'dummy_trd']
    # attached_mock.return_value = devices
    # popen_mock.return_value = self.create_popen_mock()
    # apk_path = 'dummy_apk_path'
    # stall(apk_path)
    # self.assertEqual(1, attached_mock.call_count)
    # self.assert_popen_mock(popen_mock, 3,
    # ['adb', '-s', devices[0], stall_key, apk_path],
    # ['adb', '-s', devices[1], stall_key, apk_path],
    # ['adb', '-s', devices[2], stall_key, apk_path])
    #
    # def test_pull_apk_no_package(self, popen_mock):
    # popen_mock.return_value = self.create_popen_mock()
    # package = 'dummy.package'
    # device = 'dummy_device'
    # local_dir = 'local_dir'
    # dumpey._pull_apk(package, device, local_dir)
    # self.assert_popen_mock(popen_mock, 1,
    # ['adb', '-s', device, 'shell', 'pm', 'path',
    # package])
    #
    # def test_pull_apk_multiple(self, popen_mock):
    # popen_mock.return_value = self.create_popen_mock(
    # out='package:fst\npackage:snd')
    # package = 'dummy.package'
    # device = 'dummy_device'
    # local_dir = 'local_dir'
    # dumpey._pull_apk(package, device, local_dir)
    # popen_mock.assert_called('1')
    # self.assert_popen_mock(popen_mock, 1,
    # ['adb', '-s', device, 'shell', 'pm', 'path',
    # package])
    #
    # def test_pull_apk_ok(self, popen_mock):
    # popen_mock.return_value = self.create_popen_mock(out='package:fst\n')
    # package = 'dummy.package'
    # device = 'dummy_device'
    # local_dir = 'local_dir'
    #
    # apk_name = 'fst'
    # name = device + '_' + apk_name
    # local_file = os.path.join(local_dir, name)
    #
    # dumpey._pull_apk(package, device, local_dir)
    # self.assert_popen_mock(popen_mock, 2,
    # ['adb', '-s', device, 'shell', 'pm', 'path',
    # package],
    # ['adb', '-s', device, 'pull', '-p', apk_name,
    # local_file])
    #
    # @mock.patch('dumpey.dumpey.attached_devices')
    # def test_monkey(self, attached_mock, popen_mock):
    # devices = ['device_fst', 'device_snd']
    # attached_mock.return_value = devices
    # popen_mock.return_value = self.create_popen_mock()
    # package = 'dummy.package'
    # seed = 123
    # before = mock.Mock()
    # after = mock.Mock()
    # dumpey.monkey(package, seed=123, before=before, after=after)
    # self.assert_popen_mock(popen_mock, 2,
    # ['adb', '-s', devices[0], 'shell', 'monkey',
    # '-p', package, '-s', str(seed), str(1000)],
    # ['adb', '-s', devices[1], 'shell', 'monkey',
    # '-p', package, '-s', str(seed), str(1000)])
    # self.assertEqual(2, before.call_count)
    # self.assertEqual(2, after.call_count)
    #
    # def test_pid_ok(self, popen_mock):
    # raw = 'root     31187 2    0     0    ffffffff 00000000 S dummy.package'
    # popen_mock.return_value = self.create_popen_mock(out=raw)
    # package = 'dummy.package'
    # device = 'dummy_device'
    # out = dumpey.pid(package, device)
    # self.assertEqual(out, '31187')
    # self.assert_popen_mock(popen_mock, 1,
    # ['adb', '-s', device, 'shell', 'ps'])
    #
    # def test_pid_retry(self, popen_mock):
    # popen_mock.return_value = self.create_popen_mock()
    # package = 'dummy.package'
    # device = 'dummy_device'
    # self.assertRaises(Exception, dumpey.pid, package, device)
    #     self.assert_popen_mock(popen_mock, 3,
    #                            ['adb', '-s', device, 'shell', 'monkey', '-p',
    #                             package, '-s', str(0), str(1)],
    #                            ['adb', '-s', device, 'shell', 'ps'])
    #
    # def test_remove_file(self, popen_mock):
    #     popen_mock.return_value = self.create_popen_mock()
    #     remote_path = 'dummy_file'
    #     device = 'dummy_device'
    #     dumpey.remove_file(remote_path, device)
    #     self.assert_popen_mock(popen_mock, 1,
    #                            ['adb', '-s', device, 'shell', 'rm', '-f',
    #                             remote_path])
    #
    # def test_file_size_ok(self, popen_mock):
    #     raw = '-rw-r--r-- root   root        132 1970-01-01 01:00 dummy_file'
    #     popen_mock.return_value = self.create_popen_mock(out=raw)
    #     remote_path = 'dummy_file'
    #     device = 'dummy_device'
    #     out = dumpey.file_size(remote_path, device)
    #     self.assertEqual('132', out)
    #     self.assert_popen_mock(popen_mock, 1,
    #                            ['adb', '-s', device, 'shell', 'ls', '-l',
    #                             remote_path])
    #
    # def test_file_size_raise(self, popen_mock):
    #     raw = 'dummy_file: No such file or directory'
    #     popen_mock.return_value = self.create_popen_mock(out=raw)
    #     remote_path = 'dummy_file'
    #     device = 'dummy_device'
    #     self.assertRaises(Exception, dumpey.file_size, remote_path, device)
    #     self.assert_popen_mock(popen_mock, 1,
    #                            ['adb', '-s', device, 'shell', 'ls', '-l',
    #                             remote_path])
    #
    # def test_dump_heap_bad_version(self, popen_mock):
    #     popen_mock.return_value = self.create_popen_mock(out='10\r')
    #     package = 'dummy.package'
    #     device = 'dummy_device'
    #     local_dir = 'dummy_dir'
    #     dumpey._dump_heap(package, device, local_dir)
    #     self.assert_popen_mock(popen_mock, 1,
    #                            ['adb', '-s', device, 'shell', 'getprop',
    #                             'ro.build.version.sdk'])
    #
    # @mock.patch('dumpey.dumpey.api_version')
    # @mock.patch('dumpey.dumpey.pid')
    # def test_dump_heap(self, pid_mock, api_mock, popen_mock):
    #     pid_mock.return_value = '12345'
    #     api_mock.return_value = '18'

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