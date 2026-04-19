#!/bin/sh
# incus daemon wrapper 
# regardless --logfile option incus prints some messages on stderr at start, they
# are printed in log file as well, so just ignore stderr here 

if [ "$1" != "daemon" ]; then
    echo >&2 "This is a wrapper script for incus, executed by service scripts."
    echo >&2 "Use /usr/bin/incus to run incus manually."
    exit 1
fi

exec 1>>/dev/null
exec 2>&1
exec /usr/bin/incus "$@"
