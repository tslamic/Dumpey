#!/bin/bash
#
# Runs the monkey on all devices/emulators detected by "adb devices"
# Assumes the appropriate tools (adb, hprof-conv) are included in the path.

SEED=$RANDOM
EVENTS=1000
PACKAGE=

usage() {
    echo "Usage: -p <package> [-s <integer>] [-e <integer>]"
    exit 1
}

exec_monkey() {
    local devices=($(adb devices | awk 'NF && NR>1 {print $1}'))
    for device in "${devices[@]}"
    do
        adb -s "$device" shell monkey -p "$PACKAGE" -s $SEED $EVENTS
    done
}

while getopts ":p:s:e:" opt; do
    case $opt in
        s) SEED="$OPTARG";;
        p) PACKAGE="$OPTARG";;
        e) EVENTS="$OPTARG";;
        *) usage;;
    esac
done

if [ "${PACKAGE}" ]; then
    exec_monkey
else 
    usage
fi
