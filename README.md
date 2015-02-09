# Dumpey

Android - or, more precisely, its debug bridge -  has a very handy tool called _the monkey_. Its purpose is to stress-test your app by generating pseudo-random user events in a repeatable manner. Sometimes, the usage is a bit clunky or unclear. Dumpey helps you

- run the monkey on multiple devices or emulators and
- make converted memory heap dumps before and after it

Dumpey is, currently, a collection of three *UNIX* scripts:

 - `monkey` capable of running the monkey on all attached devices/emulators
 - `memdmp` capable of extracting and converting heap dumps from a device/emulator to a local drive
 - `dumpey` capable of extracting and converting heap dumps before and after running the monkey, on all attached devices/emulators

### monkey

Three options: `p`, `s` and `e`:

 - `-p` denotes the package name and is *required*.
 - `-s` is the seed value. If missing, a random generated number will be used instead. 
 - `-e` is the number of events you wish to generate. It defaults to 10000.

Running it is as simple as:

```
$ ./monkey.sh -p your.package.name
```

or as complicated as 

```
$ ./monkey.sh -p your.package.name -s 12345 -e 5000
```

### memdmp

Three options, all required:

 - `-p` denotes the package name.
 - `-s` is the device/emulator serial number.
 - `-f` is the memory dump destination file. If it doesn't exist, it will be created.

An example:

```
$ ./memdmp.sh -s SH48HWM03500 -p your.package.name -f heapdumps/my_heap_dump.hprof
```

This will extract a converted memory heap dump to `heapdumps/my_heap_dump.hprof` file. All you have to do is open it with MAT.

### dumpey

6 options this time:

 - `-p` denotes the package name and is required.
 - `-s` is the seed value. If missing, a random generated number will be used instead. 
 - `-e` is the number of events you wish to generate. It defaults to 10000.
 - `-b` will triger memory dumps before the monkey.
 - `-a` will triger memory dumps after the monkey.
 - `-d` denotes the directory where dumps will be put. Required if either `b` or `a` (or both) is set.

Also, it expects the _memdmp_ script to be in the same directory. 

Usage remains simple. To do no memory dumps whatsoever and to behave exactly the same as the _monkey_ script, do:

```
$ ./dumpey.sh -p your.package.name
```

To add memory dumps before doing the monkey, do:

```
$ ./dumpey.sh -p your.package.name -b -d heapdumps/
```

The converted memory dump will be put in the `heapdumps` directory. If, for example, one of your attached devices is `SH48HWM03500`, the memory dump file from it will be named `SH48HWM03500-before.hprof`. 

To only do memory dumps after the monkey, change `-b` to `-a`:

```
$ ./dumpey.sh -p your.package.name -a -d heapdumps/
```

As you can imagine, the output file will be named `SH48HWM03500-after.hprof`, and will reside in the `heapdumps` directory.

Finally, to do dumps before and after, and to shorten the syntax, do:

```
$ ./dumpey.sh -p your.package.name -bad heapdumps/
```

### License

	The MIT License (MIT)
	
	Copyright (c) 2015 Tadej Slamic
	
	Permission is hereby granted, free of charge, to any person obtaining a copy
	of this software and associated documentation files (the "Software"), to deal
	in the Software without restriction, including without limitation the rights
	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
	copies of the Software, and to permit persons to whom the Software is
	furnished to do so, subject to the following conditions:
	
	The above copyright notice and this permission notice shall be included in all
	copies or substantial portions of the Software.
	
	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
	SOFTWARE.