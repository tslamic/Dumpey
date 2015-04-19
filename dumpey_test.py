import unittest

import dumpey as du


class TestStringMethods(unittest.TestCase):
    def test_decor_split(self):
        s = ' this\n is \n a\n   test'
        self.assertEqual(du._decor_split(s), ['this', 'is', 'a', 'test'])
        t = ''
        self.assertEqual(du._decor_split(t), [])

    def test_decor_package(self):
        s = 'package:test.package'
        self.assertEqual(du._decor_package(s), ['test.package'])
        t = ''
        self.assertEqual(du._decor_package(t), [])

    def test_isupper(self):
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