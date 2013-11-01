#!/bin/bash 

REACH=$1

if [ -z "$REACH" ] || [ -z "${REACH##*[!0-9]*}" ] || [ "$REACH" -lt "2" ]; then
	echo 0
	exit 0
fi

n=2
res=2
for ((i=1, pow=n; pow<=REACH; i++)); do
	if [ $(( $REACH % $pow )) -eq 0 ]; then
		res=$pow
	fi
	((pow *= n));
done

echo $res
exit 0