import unittest
import subprocess

import mock

import dumpey


@mock.patch('subprocess.Popen.communicate')
@mock.patch('subprocess.Popen')
class DumpeyTest(unittest.TestCase):
    def setUp(self):
        self.d = dumpey.Dumpey()
        self.device = '4df1e80e3cd26ff3'
        self.devices = [self.device, '3ef1e20e3ef26cb3']

    def tearDown(self):
        self.d = self.device = self.devices = None

    def test_adb_simple(self, popen_mock, communicate_mock):
        popen_mock.return_value = self.create_popen_mock()
        out = self.d.adb(['test'])
        self.assertEqual(out, '')
        popen_mock.assert_called_with(['adb', 'test'], stdout=subprocess.PIPE)


    def test_adb_raise(self, popen_mock, communicate_mock):
        popen_mock.return_value = self.create_popen_mock(1)
        self.assertRaises(Exception, self.d.adb, ['test'])
        popen_mock.assert_called_with(['adb', 'test'], stdout=subprocess.PIPE)


    def test_adb_decor(self, popen_mock, communicate_mock):
        popen_mock.return_value = self.create_popen_mock(out='fst\nsnd')
        out = self.d.adb(['test'], decor=lambda l: l.split('\n'))
        self.assertEqual(out, ['fst', 'snd'])
        popen_mock.assert_called_with(['adb', 'test'], stdout=subprocess.PIPE)


    def test_adb_device(self, popen_mock, communicate_mock):
        popen_mock.return_value = self.create_popen_mock()
        out = self.d.adb(['test'], 'device')
        self.assertEqual(out, '')
        popen_mock.assert_called_with(['adb', '-s', 'device', 'test'],
                                      stdout=subprocess.PIPE)


    def test_attached_devices(self, popen_mock, communicate_mock):
        raw_out = '''List of devices attached
                     4df1e80e3cd26ff3	device

                  '''
        popen_mock.return_value = self.create_popen_mock(out=raw_out)
        out = self.d.attached_devices()
        self.assertEqual(out, ['4df1e80e3cd26ff3'])
        popen_mock.assert_called_with(['adb', 'devices'],
                                      stdout=subprocess.PIPE)

    def test_attached_devices_raise(self, popen_mock, communicate_mock):
        popen_mock.return_value = self.create_popen_mock()
        self.assertRaises(Exception, self.d.attached_devices)
        popen_mock.assert_called_with(['adb', 'devices'],
                                      stdout=subprocess.PIPE)

    def test_api_version(self, popen_mock, communicate_mock):
        popen_mock.return_value = self.create_popen_mock(out='18\r')
        out = self.d.api_version(self.device)
        self.assertEqual(out, '18')
        popen_mock.assert_called

    def create_popen_mock(self, exit_value=0, out=None, err=None):
        if out is None:
            out = ''
        if err is None:
            err = ''
        popen_mock = mock.MagicMock()
        popen_mock.poll = mock.Mock(return_value=exit_value)
        popen_mock.communicate = mock.Mock(return_value=(out, err))
        return popen_mock

    def adb_called_with(self, popen_mock, string, *args):
        popen_mock.assert_called_with(self.mock_command(string, args),
                                      stdout=subprocess.PIPE)

    def mock_command(self, string, *args):
        command = (string % args) if args else string
        lst = command.split(' ')
        return command.split(' ')

    def mock_call(self, string, *args):
        return mock.call(self.mock_command(string, args),
                         stdout=subprocess.PIPE)


        # def test_install(self, attached_mock, adb_mock):
        # self.expect('adb -s dummy install test', None)
        # d.install('test', ['dummy'])
        #
        # self.expect('adb -s mock_device install test', None)
        # d.install('test', [])
        # d.install('test')

        # def test_uninstall(self, attached_mock, adb_mock):
        # self.expect('adb -s dummy uninstall test', None)
        # d.uninstall('test', ['dummy'])
        #
        # self.expect('adb -s mock_device uninstall test', None)
        # d.uninstall('test', [])
        # d.uninstall('test')
        #


        # def test_pull_apk(self, attached_mock, adb_mock):
        # device = 'dummy_device'
        # file_name = 'dummy_file'
        # local = '%s_%s' % (device, file_name)
        #
        # self.push_validator('adb -s dummy shell pm path com.package',
        # d._decor_package)
        # c = 'adb -s dummy pull -p %s %s' % (d._REMOTE_HEAP_DUMP_PATH, local)
        # self.push_validator(c, None)
        # d.pull_apk('com.package', [device], local)
        #
        #
        # def test_decor_split(self, attached_mock, adb_mock):
        # s = ' this '
        # self.assertEqual(d._decor_split(s), ['this'])
        # s = ' this\n is \n a\n   test'
        # self.assertEqual(d._decor_split(s), ['this', 'is', 'a', 'test'])
        # for s in ['', ' ', '   ', '\t', '\t\r', '\n']:
        # self.assertEqual(d._decor_split(s), [])
        #
        # def test_decor_package(self, attached_mock, adb_mock):
        # s = 'package:test.package'
        # self.assertEqual(d._decor_package(s), ['test.package'])
        # for s in ['', ' ', '   ', '\t', '\t\r', '\n']:
        # self.assertEqual(d._decor_package(s), [])
        #
        # def test_split(self, attached_mock, adb_mock):
        # s = 'hello world'
        # self.assertEqual(s.split(), ['hello', 'world'])
        # # check that s.split fails when the separator is not a string
        # with self.assertRaises(TypeError):
        # s.split(2)


if __name__ == '__main__':
    unittest.main()