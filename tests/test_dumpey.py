from dumpey import dumpey

import subprocess
import unittest
import mock
import re


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

    LOCAL_DIR = 'local_dir'

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
        self.assert_called(compile_mock, 1)
        self.assert_called(package_list_mock, 0)
        self.assert_called(popen_mock, 0)
        self.assert_called(f, 0)

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
        self.assert_called(compile_mock, 1)
        self.assert_called(package_list_mock, 3)
        self.assert_called(f, 1)
        self.assert_called(popen_mock, 0)

    def package_iter(self, compile_mock, package_list_mock, popen_mock,
                     packages, devices, expected, fcount):
        package_list_mock.return_value = packages
        f = mock.Mock()
        out = dumpey._package_iter("", devices, f)
        self.assertEquals(expected, out)
        self.assert_called(compile_mock, 1)
        self.assert_called(package_list_mock, len(devices))
        self.assert_called(f, fcount)
        self.assert_called(popen_mock, 0)

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
        self.assert_called(popen_mock, 0)

    def test_clear_data_raise(self, popen_mock):
        self.assertRaises(Exception, dumpey.clear_data)
        self.assert_called(popen_mock, 0)

    def test_clear_data_package(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        package = DumpeyTest.PACKAGE_1
        devices = DumpeyTest.DEVICES
        dumpey.clear_data(package=package, devices=devices)
        for device in devices:
            self.assert_popen_mock(popen_mock, len(devices),
                                   ['adb', '-s', device, "shell", "pm",
                                    "clear", package])

    def test_clear_data_one(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        package = DumpeyTest.PACKAGE_1
        device = DumpeyTest.DEVICE_1
        dumpey._clear_data(package, device)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, "shell", "pm", "clear",
                                package])

    def test_split_whitespace(self, popen_mock):
        fst = "a b  c   d    e     f      g       h"
        snd = "a       b      c     d    e   f  g h"
        res = ["a", "b", "c", "d", "e", "f", "g", "h"]
        self.assertEquals(dumpey._split_whitespace(fst), res)
        self.assertEquals(dumpey._split_whitespace(snd), res)
        self.assert_called(popen_mock, 0)

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

    # MISSING TEST INSTALL

    # MISSING TEST UNINSTALL

    def test_package_list_no_regex(self, popen_mock):
        package = DumpeyTest.PACKAGE_1
        raw = "\npackage:%s\n" % package
        popen_mock.return_value = self.create_popen_mock(out=raw)
        device = DumpeyTest.DEVICE_1
        out = dumpey._package_list(device, None)
        self.assertEquals([package], out)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'pm', 'list',
                                'packages'])

    def test_package_list(self, popen_mock):
        package = DumpeyTest.PACKAGE_1
        raw = "\npackage:%s\npackage:%s\n" % (package, DumpeyTest.PACKAGE_2)
        popen_mock.return_value = self.create_popen_mock(out=raw)
        device = DumpeyTest.DEVICE_1
        regex = re.compile("fst")
        out = dumpey._package_list(device, regex)
        self.assertEquals([package], out)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'pm', 'list',
                                'packages'])

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

    def test_reboot(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        devices = DumpeyTest.DEVICES
        dumpey.reboot(devices)
        self.assert_popen_mock(popen_mock, 3,
                               ['adb', '-s', DumpeyTest.DEVICE_1, 'reboot'],
                               ['adb', '-s', DumpeyTest.DEVICE_2, 'reboot'],
                               ['adb', '-s', DumpeyTest.DEVICE_3, 'reboot'])

    def test_remove_file(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        remote = DumpeyTest.DUMMY
        device = DumpeyTest.DEVICE_1
        dumpey.remove_file(remote, device)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'rm', '-f',
                                remote])

    @mock.patch('dumpey.dumpey.pull', autospec=True)
    @mock.patch('dumpey.dumpey.remove_file', autospec=True)
    def test_snapshot(self, remove_mock, pull_mock, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        device = DumpeyTest.DEVICE_1
        dumpey._screenshot(device, DumpeyTest.LOCAL_DIR)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'screencap',
                                dumpey._REMOTE_SCREENSHOT_PATH])
        self.assert_called(pull_mock, 1)
        self.assert_called(remove_mock, 1)

    @mock.patch('dumpey.dumpey.attached_devices', autospec=True)
    def test_snapshots_raise(self, attached_mock, popen_mock):
        attached_mock.return_value = DumpeyTest.PACKAGES
        self.assertRaises(Exception, dumpey.snapshots)
        self.assert_called(popen_mock, 0)

    @mock.patch('dumpey.dumpey.attached_devices', autospec=True)
    def test_snapshots(self, attached_mock, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        device = DumpeyTest.DEVICE_1
        attached_mock.return_value = [device]
        dumpey.snapshots()
        self.assert_popen_mock(popen_mock, 3,  # snap + pull + remove
                               ['adb', '-s', device, 'shell', 'screencap',
                                dumpey._REMOTE_SCREENSHOT_PATH])

    def test_uninstall_package(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        package = DumpeyTest.PACKAGE_1
        device = DumpeyTest.DEVICE_1
        dumpey._uninstall_package(package, device)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'uninstall', package])

    def test_decor_split(self, popen_mock):
        args = ' fst\n   snd\ntrd    \nfth'
        self.assertEqual(dumpey._decor_split(args),
                         ['fst', 'snd', 'trd', 'fth'])
        self.assertEqual(dumpey._decor_split(''), [])
        self.assert_called(popen_mock, 0)

    def test_decor_package(self, popen_mock):
        args = ' package:fst\n   package:snd\npackage:trd    \npackage:fth'
        self.assertEqual(dumpey._decor_package(args),
                         ['fst', 'snd', 'trd', 'fth'])
        self.assertEqual(dumpey._decor_package(''), [])
        self.assert_called(popen_mock, 0)

    def test_pull_apk_no_package(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        package = DumpeyTest.PACKAGE_1
        device = DumpeyTest.DEVICE_1
        local_dir = DumpeyTest.LOCAL_DIR
        dumpey._pull_apk(package, device, local_dir)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'pm', 'path',
                                package])

    def test_pull_apk_multiple(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock(
            out='package:fst\npackage:snd'
        )
        package = DumpeyTest.PACKAGE_1
        device = DumpeyTest.DEVICE_1
        local_dir = DumpeyTest.LOCAL_DIR
        dumpey._pull_apk(package, device, local_dir)
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'pm', 'path',
                                package])

    def test_pull_apk_ok(self, popen_mock):
        package = DumpeyTest.PACKAGE_1
        package_path = package + "apk_path.apk"
        raw = 'package:%s\n' % package_path
        popen_mock.return_value = self.create_popen_mock(out=raw)

        device = DumpeyTest.DEVICE_1
        local_dir = DumpeyTest.LOCAL_DIR

        dumpey._pull_apk(package, device, local_dir)
        self.assert_popen_mock(popen_mock, 2,  # path + pull
                               ['adb', '-s', device, 'shell', 'pm', 'path',
                                package])

    @mock.patch('dumpey.dumpey.attached_devices')
    def test_monkey(self, attached_mock, popen_mock):
        devices = DumpeyTest.DEVICES
        attached_mock.return_value = devices
        popen_mock.return_value = self.create_popen_mock()
        package = DumpeyTest.PACKAGE_1
        seed = 123
        before = mock.Mock()
        after = mock.Mock()
        dumpey.monkey(package, seed=seed, before=before, after=after)

        size = len(devices)
        for device in devices:
            self.assert_popen_mock(popen_mock, size,
                                   ['adb', '-s', device, 'shell', 'monkey',
                                    '-p', package, '-s', str(seed), str(1000)])
        self.assert_called(before, size)
        self.assert_called(after, size)

    def test_pid_ok(self, popen_mock):
        package = DumpeyTest.PACKAGE_1
        device = DumpeyTest.DEVICE_1
        raw = 'root   31187 2   0   0   ffffffff 00000000 S %s' % package
        popen_mock.return_value = self.create_popen_mock(out=raw)
        out = dumpey.pid(package, device)
        self.assertEqual(out, '31187')
        self.assert_popen_mock(popen_mock, 1,
                               ['adb', '-s', device, 'shell', 'ps'])

    def test_pid_retry(self, popen_mock):
        popen_mock.return_value = self.create_popen_mock()
        package = DumpeyTest.PACKAGE_1
        device = DumpeyTest.DEVICE_1
        self.assertRaises(Exception, dumpey.pid, package, device)
        self.assert_popen_mock(popen_mock, 3,
                               ['adb', '-s', device, 'shell', 'monkey', '-p',
                                package, '-s', str(0), str(1)],
                               ['adb', '-s', device, 'shell', 'ps'])

    @mock.patch('dumpey.dumpey.api_version', return_value=10)
    def test_dump_heap_bad_version(self, api_mock, popen_mock):
        package = DumpeyTest.PACKAGE_1
        device = DumpeyTest.DEVICE_1
        local_dir = DumpeyTest.LOCAL_DIR
        dumpey._dump_heap(package, device, local_dir)
        self.assert_called(api_mock, 1)
        self.assert_called(popen_mock, 0)

    def test_to_str(self, popen_mock):
        self.assertEquals("a_b_c", dumpey._to_str(["a", "b", "c"], "_"))
        self.assertEquals("a_b", dumpey._to_str(["a", "b", None], "_"))
        self.assert_called(popen_mock, 0)

    def test_generate_name(self, popen_mock):
        self.assertEquals("device_test",
                          dumpey._generate_name("device", "test"))
        self.assertEquals("1_device_test",
                          dumpey._generate_name("1.device", "test"))
        self.assertEquals("de_vice_test.png",
                          dumpey._generate_name("de.vice", "test", "png"))
        self.assertEquals("de_vice_a_b.png",
                          dumpey._generate_name("de.vice", ["a", "b"], "png"))
        self.assertEquals("a_b_c_d_e.test",
                          dumpey._generate_name("a!b,c", ["d", "e"], "test"))
        self.assert_called(popen_mock, 0)

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
        self.assert_called(popen_mock, times)
        for arg in args:
            popen_mock.assert_any_call(arg, stdout=subprocess.PIPE)

    def assert_called(self, mock_obj, count):
        self.assertEquals(count, mock_obj.call_count)


if __name__ == '__main__':
    unittest.main()
