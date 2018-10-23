#!/bin/bash

App="/home/zhangwt/storage_drl_agents/run.py"

param_count=$#
agent=$2
load=$3
agents=(dqn a2c acktr ppo)
source activate force

function killProcess() {
	NAME=$1
	# echo $NAME

	PID=$(ps -ef | grep $NAME |grep -v "grep" | awk '{print $2}')
	echo "PID: $PID"
	kill -9 $PID
	echo "service stop "
}

function start() {
	COUNT=$(ps -ef |grep $App |grep -v "grep" |wc -l)
	if [ $COUNT -eq 0 ]; then
	    if [ $param_count -eq 2 ]; then
            if echo "${agents[@]}" | grep -w $agent &>/dev/null; then
                nohup python $App --agent $agent >>nohup.out 2>&1 &
                echo "$agent service started successfully"
            else
                echo "$agent is not valid"
            fi
        else
            nohup python $App >>nohup.out 2>&1 &
            echo " service started successfully"
        fi
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