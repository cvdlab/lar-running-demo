#!/bin/sh

JAVA=$(which java)

if [ -z "$JAVA" ]; then
    echo "Cannot find a valid java installation (java executable missing)"
	exit 1
fi

if [ -z "$JAVA_HOME" ]; then
    echo "Cannot find a valid java installation ($JAVA_HOME missing)"
	exit 1
fi

exit 0