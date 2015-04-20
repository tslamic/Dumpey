import unittest

import dumpey as d


class DumpeyTest(unittest.TestCase):
    def test_decor_split(self):
        s = ' this '
        self.assertEqual(d._decor_split(s), ['this'])
        s = ' this\n is \n a\n   test'
        self.assertEqual(d._decor_split(s), ['this', 'is', 'a', 'test'])
        for s in ['', ' ', '   ', '\t', '\t\r', '\n']:
            self.assertEqual(d._decor_split(s), [])

    def test_decor_package(self):
        s = 'package:test.package'
        self.assertEqual(d._decor_package(s), ['test.package'])
        for s in ['', ' ', '   ', '\t', '\t\r', '\n']:
            self.assertEqual(d._decor_package(s), [])

    def test_install(self):
        self.assertTrue('FOO'.isupper())
        self.assertFalse('Foo'.isupper())

    def test_split(self):
        s = 'hello world'
        self.assertEqual(s.split(), ['hello', 'world'])
        # check that s.split fails when the separator is not a string
        with self.assertRaises(TypeError):
            s.split(2)


if __name__ == '__main__':
    unittest.main()