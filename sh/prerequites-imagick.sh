#!/bin/sh

CONVERT=$(which convert)

if [ -z "$CONVERT" ]; then
    echo "Cannot find a valid imagemagick installation"
	exit 1
fi

exit 0