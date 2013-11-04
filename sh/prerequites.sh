#!/bin/sh

PYTHON=$(which python)
CONVERT=$(which convert)
DCM2PNM=$(which dcm2pnm)
JAVA=$(which java)

if [ -z "$PYTHON" ]; then
    echo "Cannot find a valid python interpreter"
	exit 1
fi

$PYTHON $(pwd)/py/packages/check-packages.py

if [ $? -ne 0 ]; then
        echo "Missing python modules, install them"
        exit 1
fi

if [ -z "$JAVA" ]; then
    echo "Cannot find a valid java installation (java executable missing)"
	exit 1
fi

if [ -z "$JAVA_HOME" ]; then
    echo "Cannot find a valid java installation ($JAVA_HOME missing)"
	exit 1
fi

if [ -z "$CONVERT" ]; then
    echo "Cannot find a valid imagemagick installation"
	exit 1
fi

if [ -z "$DCM2PNM" ]; then
    echo "Cannot find a valid dcm2pnm installation"
	exit 1
fi

exit 0