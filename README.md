Dumpey is a simple Python script that can

 - download any installed APK from a device
 - extract a converted memory dump
 - run the monkey stress test AND extract memory dumps before and after it
 - install and uninstall packages

on all attached devices, or just the ones you specify.

### How to cherry pick devices?

The `-d` flag is what you’re after. No flag in your commands means **all** 
attached devices will be used. If you wish to execute dumpey on your favourite 
device with a serial `OMG_FAV_DEVICE`, this does the job:

```
$ dumpey <command> -d OMG_FAV_DEVICE
```

To add a few other devices, say `DEVICE_1`, `DEVICE_2` and `DEVICE_3`, 
the command is:

```
$ dumpey <command> -d OMG_FAV_DEVICE DEVICE_1 DEVICE_2 DEVICE_3
```

### Download an APK

Let’s try and download the Youtube APK, installed on any decent Android device. 
If you don’t already know the package name, you’ll have to find it. Easy peasy:

```
$ dumpey -l youtube
$ Installed packages on 4df1e80e3cd26ff3: 
$ com.google.android.youtube
```

Then use the package name to download the APK:

```
$ dumpey -a com.google.android.youtube
$ Transferred 1 of 1
$ downloaded to …
``

Done! If you want the APK to be downloaded to a specific directory do:

```
$ dumpey -a com.google.android.youtube /path/to/the/desired/dir
```

### Extract a converted memory dump

Want to pull a Youtube memory dump you can view in MAT? Execute

```
$ dumpey -e com.google.android.youtube
```

Want it in a specific directory? Simple: 

```
$ dumpey -e com.google.android.youtube /path/to/the/desired/dir
```

### Monkeying around

For a simple stress test, this’ll do:

```
$ dumpey -m com.google.android.youtube
```

Optional flags include:

- `-s` : seed value (integer)
- `-e` : number of events (integer)
- `-h` : heap dumps: use `b` to do a dump before monkey, `a` to do a dump after monkey, or `ab` or `ba` to do it before and afer
- `-d` : directory to put the dumps in. By default they go into your current working directory. 


### Install and uninstall packages

The name itself tells the story. To install do

```
$ dumpey -i /path/to/my/apk
```

and to uninstall:

```
$ dumpey -u com.google.android.youtube
```

### Have a suggestion, a fix, a complaint, a new implemented feature?
Open an issue, or better yet, create a pull request! 

### License