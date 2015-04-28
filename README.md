Dumpey is a simple Python script that helps you

 - get any installed APK
 - stop and clear data of any package
 - do a converted memory dump
 - create a series of snapshots
 - run the monkey stress test AND extract memory dumps before and after it
 - install and uninstall multiple packages
 - list installed packages

on all attached devices, or just the ones you specify. 

Most commands can be executed with a **package name** or a **regex string**. If a command is executed with a regex and multiple packages match, Dumpey will tell you about them, but won't do anything. 
To allow Dumpey to act on all matching packages, a `-f` or `--force` flag is required.

To cherry pick devices, specify the serials with a `-s` or `--serials` flag: 
```
<dumpey-command> -s 32041cce74b52267
```

### Examples

```
$ dumpey a -r youtube
```

will download the Youtube APK to your current working directory. Command `a` downloads APKs. Flag `-r` denotes a regex string.

```
$ dumpey i /path/to/multiple/apks/dir
```

will install every APK it'll find in the specified directory. Command `i` installs APKs from given directories. You can use flag `-r` or `--recursive` and Dumpey will install every apk from subdirectories, too.

```
$ dumpey h -r youtube 
```
will create a converted hprof file in your current working directory. The file contains a heap dump from the Youtube app. Just open it with MAT.


```
$ dumpey u com.package.example
```

will uninstall the com.package.example from all attached devices.

```
$ dumpey r -s 32041cce74b52267
```

will reboot the device with serial number 32041cce74b52267. 

```
$ dumpey m com.package.example --dump ba
```

will create a hprof file with a memory dump from com.package.example. It'll then do a monkey stress test. After monkey is done, another hprof file with a memory dump after the monkey is created. All you have to do is open them in MAT and compare. `ba` denotes **b**efore and **a**fter 

### But wait, there's more!

Here's the list of all Dumpey commands: 

```
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
```

each command accepts a `-h` or `--help` flag which'll tell you the various ways to use Dumpey.

Dumpey can also serve as a library, since it enables you to interact with the ADB, with some of the plumbing taken care of. 

### Install

`pip install dumpey`


### Have a suggestion, a fix, a complaint or a feature request?

Open an issue, or better yet, create a pull request!

### License

Apache 2.0