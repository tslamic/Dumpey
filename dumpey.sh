#!/bin/bash
#
# Runs the monkey on all devices/emulators detected by "adb devices" and dumps
# the heap before, after, of both, if specified.
#
# Assumes the appropriate tools (adb, hprof-conv) are included in the path.

SEED=$RANDOM
EVENTS=500
PACKAGE=""
BEFORE=false
AFTER=false
DIR=""

usage() {
    echo "Usage: -p <package> [-s <integer>] [-e <integer>] [-b] [-a] [-d <dir>]"
	exit 1
}

err() {
	echo "$1" >&2
	exit 1
}

create_file_name() {
	local serial=$(echo "$1" | sed -e 's/[^A-Za-z0-9_-]/_/g')
	local extra=$2
	echo "$DIR/$serial-$extra.hprof"
}

dump_heap() {
	local device="$1"
	local file=$(create_file_name "$device" "$2")
	
	./memdmp.sh -s "$device" -p "$PACKAGE" -f "$file"
	
	if [[ "$?" -ne 0 ]]; then
	  err "Failed to dump heap on $device"
	fi
}

exec_monkey() {
	local devices=($(adb devices | awk 'NF && NR>1 {print $1}'))		
	for device in "${devices[@]}"
	do
		if [ $BEFORE = true ]; then dump_heap $device "before"; fi
		adb -s $device shell monkey -p $PACKAGE -s $SEED $EVENTS
		if [ $AFTER = true ]; then dump_heap $device "after"; fi
	done
}

while getopts ":p:s:e:bad:" opt; do
    case $opt in
        s) SEED="$OPTARG";;
        p) PACKAGE="$OPTARG";;
        e) EVENTS="$OPTARG";;
		b) BEFORE=true;;
		a) AFTER=true;;
		d) DIR="$OPTARG";;
        *) usage;;
    esac
done

if [ -z "${PACKAGE}" ]; then
    usage
else 
	if [ $BEFORE = true ] || [ $AFTER = true ]; then
		if [ -z "$DIR" ]; then
			err "Directory path missing."
		fi
	fi
    exec_monkey
fi