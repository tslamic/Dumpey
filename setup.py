from setuptools import setup, find_packages

with open('README.rst', 'r') as f:
    long_description = f.read()

with open('VERSION', 'r') as f:
    version = f.read().strip()

tests_require = ['mock']

setup(
    name='dumpey',
    version=version,
    packages=find_packages(),
    url='https://github.com/tslamic/Dumpey',
    license='MIT',
    author='Tadej Slamic',
    description='Android Debug Bridge utility tool',
    long_description=long_description,
    keywords='android adb utility dumpey',
    test_suite='tests',
    tests_require=tests_require,
    extras_require={
        'test': tests_require,
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
    ],
)
