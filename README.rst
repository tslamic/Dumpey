Dumpey is a simple Python script that helps you

-  pull any installed APK
-  stop and clear data of any package
-  do a memory dump
-  create a series of snapshots
-  run the monkey stress test and extract memory dumps before and/or
   after it
-  install and uninstall multiple packages
-  list installed packages

on all attached devices, or just the ones you specify. Most commands can
be executed with a specific **package name** or a **regex**.

**Dumpey expects Android platform tools to be part of the system path.**
**Currently supports Python 2.7 - 3.3, inclusive.**

.. image:: https://travis-ci.org/tslamic/Dumpey.svg?branch=master
    :target: https://travis-ci.org/tslamic/Dumpey

Get it with

::

    pip install dumpey

Examples
~~~~~~~~

If a command is executed with a regex and multiple packages are found,
Dumpey will warn you, but won't do anything unless you explicitly
specify the ``-f`` or ``--force`` flag. To cherry pick devices, specify
serials with a ``-s`` or ``--serials`` flag.

::

    $ dumpey a -r youtube

will download the Youtube APK to current working directory. Flag ``-r``
denotes a regex string.

::

    $ dumpey i -o /my/dir

will install every APK it finds in the ``/my/dir`` directory. You can
use ``-r`` or ``--recursive`` flag to install APKs from subdirectories,
too.

::

    $ dumpey h -r youtube 

will create a converted hprof file in your current working directory.
Just open it with MAT.

::

    $ dumpey u -p com.google.android.youtube

will uninstall the Youtube app from all attached devices.

::

    $ dumpey r -s 32041cce74b52267

will reboot the device with serial number 32041cce74b52267.

::

    $ dumpey c -f -r google

will force stop and clear all the data from each package that includes a
'google' string.

::

    $ dumpey m -p com.google.android.youtube --dump ba

will create a hprof file with a memory dump from the Youtube app. It'll
then do a monkey stress test. After monkey is done, another hprof file
with a memory dump after the monkey is created. All you have to do is
open them in MAT and compare. ``ba`` denotes **b**\ efore and
**a**\ fter

But wait, there's more!
~~~~~~~~~~~~~~~~~~~~~~~

Here's the list of all Dumpey commands:

::

    usage: dumpey.py [-h] {i,u,a,c,r,h,l,m,s} ...

    Dumpey, an Android Debug Bridge utility tool.

    optional arguments:
      -h, --help           show this help message and exit

    dumpey commands:
      {i,u,a,c,r,h,l,m,s}  commands
        i                  install APKs from path
        u                  uninstall apps
        a                  download APKs
        c                  stop and clear package data
        r                  reboot devices
        h                  do a heap dump
        l                  list installed packages
        m                  run the monkey
        s                  make snapshot

each command accepts a ``-h`` or ``--help`` flag which'll tell you the
various ways to use Dumpey.

Dumpey can also serve as a library, since it enables you to interact
with the ADB, with some of the plumbing taken care of.

Install
~~~~~~~

``pip install dumpey``

Have a suggestion, a fix, a complaint or feature request?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open an issue, or better yet, create a pull request!

License
~~~~~~~

The MIT License (MIT)

Copyright (c) 2015 Tadej Slamic

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
