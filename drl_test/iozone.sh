#!/bin/bash

App="iozone_test.py"
 

function killProcess() {
	NAME=$1
	# echo $NAME

	PID=$(ps -ef | grep $NAME |grep -v "grep" | awk '{print $2}')
	echo "PID: $PID"
	kill -9 $PID
	PID=$(ps -ef | grep iozone |grep -v "grep" | awk '{print $2}')
	echo "iozonePID: $PID"
	kill -9 $PID
	echo "service stop "
}

function start() {
	COUNT=$(ps -ef |grep $App |grep -v "grep" |wc -l)
	if [ $COUNT -eq 0 ]; then
	    export RSH=ssh
	    export rsh=ssh
	    export PATH="$PATH:/home/zhangwt/iozone3_479/src/current"
        nohup python $App >>nohup.out 2>&1 &
        echo " service started successfully"
    else
        echo "The service is already running"
    fi

}

function stop() {
	killProcess $App
}

function status() {
	COUNT=$(ps -ef |grep $App |grep -v "grep" |wc -l)
	if [ $COUNT -eq 0 ]; then
        echo "service not running"
    else
        echo "The service is running..."
    fi
}

function restart() {
	echo "restart"
	stop
	start
}

case "$1" in
	start )
		echo "****************"
		start
		echo "****************"
		;;
	stop )
		echo "****************"
		stop
		echo "****************"
		;;
	status )
		echo "****************"
		status
		echo "****************"
		;;
	restart )
		echo "****************"
		restart
		echo "****************"
		;;
	* )
		echo "****************"
		echo "no command"
		echo "****************"
		;;
esac