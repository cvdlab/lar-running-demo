#!/bin/sh

echo "==================="
echo "LAR Model extractor"
echo "==================="

echo "** Checking prerequisites **"

./sh/prerequites.sh

if [ $? -ne 0 ]; then
        echo "Missing prerequisites, install them (check output)."
        # exit 1
fi

echo "==================="
echo "** Input data **"

echo -n "Enter directory path [ENTER]: "
read DIRINPUT
echo -n "Enter best image file in the previous directory [ENTER]: "
read BESTIMAGE
echo -n "Number of colors to quantize (max 2) [ENTER]: "
read COLORS
echo -n "Use OpenCL (y/n): "
read -n 1 OPENCL
echo ""

if [ -z "$DIRINPUT" ] || [ ! -d "$DIRINPUT" ]; then
	echo "Wrong directory $DIRINPUT"
	# exit 1
fi

if [ -z "$BESTIMAGE" ] || [ ! -r "$DIRINPUT/$BESTIMAGE" ]; then
	echo "Wrong file $DIRINPUT/$BESTIMAGE"
	# exit 1
fi

if [ -z "$COLORS" ] || [ -z "${COLORS##*[!0-9]*}" ] || [ "$COLORS" -lt "2" ]; then
	echo "Wrong colors $COLORS"
	# exit 1
fi

if [ -z "$OPENCL" ] || [ "$OPENCL" != "y" ]; then
	echo "Not using OpenCL"
	OPENCL=0
else 
	echo "Using OpenCL for available operations"
	OPENCL=1
fi

echo "Will try to extract model from $DIRINPUT/ using color quantization ($COLORS)"
echo -n "Is ok to proceed? (y/n) > "
read -n 1 RUNSCRIPT
echo ""

if [ -z "$RUNSCRIPT" ] || [ "$RUNSCRIPT" != "y" ]; then
	echo "Aborting execution as requested"
	exit 1
fi

WORKINDIR=$(pwd)

# Generate tmp dir name
TMPDIRECTORY=$WORKINDIR/tmp/$(date | md5sum | head -c${1:-32})
echo "Using tmp directory $TMPDIRECTORY"

# Create clean dir
rm -fr $TMPDIRECTORY &> /dev/null
mkdir -p $TMPDIRECTORY &> /dev/null

if [ ! -d "$TMPDIRECTORY" ]; then
	echo "Could not create $TMPDIRECTORY. Aborting!"
	exit 1
fi

# Copy images to tmpdir
cp $DIRINPUT/* $TMPDIRECTORY &> /dev/null

# Conversion script
FIRSTFILE=$(ls $TMPDIRECTORY | sort -n | head -1)
EXTFILE="${FIRSTFILE##*.}"
COUNTFILE=1
BESTFILE=$STARTFILE

if false; then

if [ "$EXTFILE" == "png" ] || [ "$EXTFILE" == "jpg" ]; then
	for currFile in $(ls $TMPDIRECTORY) ; do
		# fileName="${currFile##*/}"
		convert -colorspace gray $TMPDIRECTORY/$currFile $TMPDIRECTORY/$COUNTFILE.png
		if [ "$BESTIMAGE" == "$currFile" ]; then
			BESTFILE=$COUNTFILE
		fi
		rm $TMPDIRECTORY/$currFile
		#
		COUNTFILE=$((COUNTFILE + 1))
	done
elif [ "$EXTFILE" == "dcm" ]; then
	for currFile in $(ls $TMPDIRECTORY) ; do
		# fileName="${currFile##*/}"
		dcm2pnm +G +on $TMPDIRECTORY/$currFile $TMPDIRECTORY/$COUNTFILE.png
		if [ "$BESTIMAGE" == "$currFile" ]; then
			BESTFILE=$COUNTFILE
		fi
		rm $TMPDIRECTORY/$currFile
		#
		COUNTFILE=$((COUNTFILE + 1))
	done
else
	echo "Unknow file extension: $EXTFILE"
	rm -fr $TMPDIRECTORY &> /dev/null
	exit 1
fi
cd $WORKINDIR

fi

# Bash py wrapper

# ... if you want to visualize...