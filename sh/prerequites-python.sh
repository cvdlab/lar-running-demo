#!/bin/sh

PYTHON=$(which python)

if [ -z "$PYTHON" ]; then
    echo "Cannot find a valid python interpreter"
	exit 1
fi

$PYTHON $(pwd)/py/packages/check-packages.py

if [ $? -ne 0 ]; then
        echo "Missing python modules, install them"
        exit 1
fi

exit 0