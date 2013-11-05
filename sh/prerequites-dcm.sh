#!/bin/sh

DCM2PNM=$(which dcm2pnm)

if [ -z "$DCM2PNM" ]; then
    echo "Cannot find a valid dcm2pnm installation"
	exit 1
fi

exit 0