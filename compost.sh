#!/bin/sh

### BEGIN INIT INFO
# Provides:          forwarderd
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Put a short description of the service here
# Description:       Put a long description of the service here
### END INIT INFO

# Change the next 3 lines to suit where you install your script and what you want to call it
DIR=/opt/cloud_compost
DAEMON=$DIR/cloud_compost.py
DAEMON_NAME=compostd

# This next line determines what user the script runs as.
# Root generally not recommended but necessary if you are using the Raspberry Pi GPIO from Python.
DAEMON_USER=root

. /lib/lsb/init-functions

do_start () {
    python $DAEMON start
}
do_stop () {
    python $DAEMON stop
}

case "$1" in

    start|stop)
        do_${1}
        ;;

    restart|reload|force-reload)
        do_stop
        do_start
        ;;

    *)
        echo "Usage: /etc/init.d/$DAEMON_NAME {start|stop|restart}"
        exit 1
        ;;

esac
exit 0
