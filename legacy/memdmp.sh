#!/bin/bash
#
# Dumps the memory from a device/emulator.
# Assumes the appropriate tools (adb, hprof-conv) are included in the path.
#
# Released under the MIT License (MIT), copyright (c) 2015 Tadej Slamic.

readonly TMP_SDCARD_HPROF_PATH="/sdcard/hprof___tmp"

SERIAL=
PACKAGE=
FILE=

usage() {
    echo "Usage: -s <serialNumber> -p <package> -f <file>"
    exit 1
}

err() {
    echo "$1" >&2
    exit 1
}

create_file() {
    local file=$1
    local dir=$(dirname "$file")
    
    mkdir -p -- "$dir" && touch -- "$file"  
    
    if [ ! -f "$file" ]; then 
        err "File $file could not be created."
    fi
}

file_size_on_device() {
    local file="$1"
    adb -s "$SERIAL" shell ls -l "$file" | awk '{print $4}'
}

dump_heap() {
    local pid="$1"
    local file="$2"
    local dir=$(dirname "$file")

    # If the tmp file already exists, remove it.
    if [ -f "$file" ]; then
        adb -s "$SERIAL" shell rm "$file"
    fi

    echo -n "Dumping heap "
    
    # Dump the heap to a tmp file on a device/emulator
    adb -s "$SERIAL" shell am dumpheap "$pid" "$file"
    
    # Beacuse the previous cmd runs as a daemon, we have to wait for it to 
    # finish: check the tmp file size continuously and stop
    # when it's not changing anymore.  
    local sleepinterval=0.5
    
    local s0=-1
    sleep $sleepinterval
    local s1=$(file_size_on_device "$file")
    
    while ((s1 > s0))
    do 
        echo -n "."
        sleep $sleepinterval
        let s0=$s1
        let s1=$(file_size_on_device "$file")
    done
    
    echo " Done"
}

extract_from_device() {
    local pid=$(adb -s "$SERIAL" shell ps | awk -v p="$PACKAGE" '$9 ~ p {print $2}')
    if [ -z "${pid}" ]; then
        err "PID for $PACKAGE not found. Is your app installed and running?"
    fi
    
    # Dump heap to tmp file on a device
    local file="$TMP_SDCARD_HPROF_PATH"
    dump_heap "$pid" "$file"
    
    # Extract
    local tmp="$FILE-nonconv"       
    create_file "$tmp"
    adb -s "$SERIAL" pull -p "$file" "$tmp"
    
    # Convert
    if [ -s "$tmp" ]; then
        create_file "$FILE"       
        hprof-conv "$tmp" "$FILE"
    else
        echo "No data to convert."
    fi
    
    # Finish
    adb -s "$SERIAL" shell rm "$file"
    rm -- "$tmp"
    
    echo "Done, converted heap extracted to $FILE"
}

exec() {
    local version=$(adb -s "$SERIAL" shell getprop ro.build.version.sdk | tr -d '\r')
    if [ "$version" -gt "10" ]; then
        extract_from_device
    else 
        err "The target device/emulator must be API 11 or above."
    fi
}

while getopts ":s:p:f:" opt; do
    case $opt in
        s) SERIAL="$OPTARG";;
        p) PACKAGE="$OPTARG";;
        f) FILE="$OPTARG";;
        *) usage;;
    esac
done

if [ "$SERIAL" -a "$PACKAGE" -a "$FILE" ]; then
    exec
else 
    usage
fi
