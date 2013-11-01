#!/bin/bash
MYSELF=`basename $0`

show_help() {
	echo "Either run without args or with"
	echo "To use args enable it with -u"
	echo "-d <input images>	: Directory containing input images"
	echo "-f <best image>		: Image to quantize on"
	echo "-q <colors>		: Number of colors to quantize (min 2)"
	echo "-c					: Use OpenCL"
}

echo "==================="
echo "LAR Model extractor"
echo "==================="

USECMDLINE=0
OPTIND=1 # Reset is necessary if getopts was used previously in the script.  It is a good idea to make this local in a function.
while getopts "h?cud:f:q:" opt; do
	case "$opt" in
		h|\?)
			show_help
			exit 0
			;;
		u)  USECMDLINE=1
			;;
		d)  DIRINPUT=$OPTARG
			;;
		f)  BESTIMAGE=$OPTARG
			;;
		q)  COLORS=$OPTARG
			;;
		c)  OPENCL=0
			;;
	esac
done
shift $((OPTIND-1)) # Shift off the options and optional --.

echo "** Checking prerequisites **"

sh ./sh/prerequites.sh

if [ $? -ne 0 ]; then
	echo "Missing prerequisites, install them (check output)."
	exit 1
fi

echo "==================="
echo "** Input data **"

if [ "$USECMDLINE" -eq "0" ]; then
	echo -n "Enter directory path [ENTER]: "
	read DIRINPUT
	echo -n "Enter best image file in the previous directory [ENTER]: "
	read BESTIMAGE
	echo -n "Number of colors to quantize (min 2) [ENTER]: "
	read COLORS
	echo -n "Use OpenCL (y/n): "
	read -n 1 OPENCL
fi

# Empty line
echo ""

if [ -z "$DIRINPUT" ] || [ ! -d "$DIRINPUT" ]; then
	echo "Wrong directory $DIRINPUT"
	exit 1
fi

if [ -z "$BESTIMAGE" ] || [ ! -r "$DIRINPUT/$BESTIMAGE" ]; then
	echo "Wrong file $DIRINPUT/$BESTIMAGE"
	exit 1
fi

if [ -z "$COLORS" ] || [ -z "${COLORS##*[!0-9]*}" ] || [ "$COLORS" -lt "2" ]; then
	echo "Wrong colors $COLORS"
	exit 1
fi

if [ -z "$OPENCL" ] || [ "$OPENCL" != "y" ]; then
	echo "Not using OpenCL"
	OPENCL=0
else 
	echo "Using OpenCL for available operations"
	OPENCL=1
fi

# Empty line
echo ""

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
TMPIMGDIRECTORY=$TMPDIRECTORY/img
mkdir -p $TMPIMGDIRECTORY &> /dev/null

if [ ! -d "$TMPIMGDIRECTORY" ]; then
	echo "Could not create $TMPIMGDIRECTORY Aborting!"
	exit 1
fi

cp $DIRINPUT/* $TMPIMGDIRECTORY &> /dev/null

# Conversion script
FIRSTFILE=$(ls $TMPIMGDIRECTORY | sort -n | head -1)
EXTFILE="${FIRSTFILE##*.}"
COUNTFILE=1
BESTFILE=$STARTFILE

echo -n "Converting input images..."
if [ "$EXTFILE" == "png" ] || [ "$EXTFILE" == "jpg" ]; then
	for currFile in $(ls $TMPIMGDIRECTORY) ; do
		# fileName="${currFile##*/}"
		convert -colorspace gray $TMPIMGDIRECTORY/$currFile $TMPIMGDIRECTORY/$COUNTFILE.png
		if [ "$BESTIMAGE" == "$currFile" ]; then
			BESTFILE=$COUNTFILE
		fi
		rm $TMPIMGDIRECTORY/$currFile
		#
		COUNTFILE=$((COUNTFILE + 1))
	done
elif [ "$EXTFILE" == "dcm" ]; then
	for currFile in $(ls $TMPIMGDIRECTORY) ; do
		# fileName="${currFile##*/}"
		dcm2pnm +G +on $TMPIMGDIRECTORY/$currFile $TMPIMGDIRECTORY/$COUNTFILE.png
		if [ "$BESTIMAGE" == "$currFile" ]; then
			BESTFILE=$COUNTFILE
		fi
		rm $TMPIMGDIRECTORY/$currFile
		#
		COUNTFILE=$((COUNTFILE + 1))
	done
else
	echo "Unknown file extension: $EXTFILE"
	rm -fr $TMPDIRECTORY &> /dev/null
	exit 1
fi

BESTFILE=$BESTFILE.png
echo -n " done. Best image is now: $BESTFILE"
echo ""

BESTIMAGE_WIDTH=$(identify -format '%w' $TMPIMGDIRECTORY/$BESTFILE)
BESTIMAGE_HEIGHT=$(identify -format '%h' $TMPIMGDIRECTORY/$BESTFILE)
TOTALCOUNT=$(ls -1 $TMPIMGDIRECTORY | wc -l)

echo "Image sizes are $BESTIMAGE_WIDTH*$BESTIMAGE_HEIGHT*$TOTALCOUNT"
if [ $(( $TOTALCOUNT % 2 )) -ne 0 ]; then
	echo "Images are odd, adding one"
	convert -size $BESTIMAGE_WIDTH\x$BESTIMAGE_HEIGHT -colorspace gray xc:black $TMPIMGDIRECTORY/$COUNTFILE.png
	TOTALCOUNT=$((TOTALCOUNT + 1))
fi

# ask for border operator dimensions
BORDER_X=$(./sh/pow2test.sh $BESTIMAGE_WIDTH)
BORDER_Y=$(./sh/pow2test.sh $BESTIMAGE_HEIGHT)
BORDER_Z=$(./sh/pow2test.sh $TOTALCOUNT)

echo -n "Suggested border operator dim $BORDER_X x $BORDER_Y x $BORDER_Z "
if [ "$BORDER_X" -eq "0" ] || [ "$BORDER_Y" -eq "0" ] || [ "$BORDER_Z" -eq "0" ]; then
	echo -n "[might be erroneous]"
fi

echo ""
echo -n "Enter new border operator dim [X*Y*Z and ENTER] [ENTER to skip]: "
read BORDERNEW

if [ ! -z "$BORDERNEW" ]; then
	BORDNEW_ARR=($(echo $BORDERNEW | tr "*" "\n"))
	
	if [ ${#BORDNEW_ARR[@]} -ne 3 ]; then
		echo "Unknown format. Aborting"
		exit 1
	fi
	
	BORDER_X=${BORDNEW_ARR[0]}
	BORDER_Y=${BORDNEW_ARR[1]}
	BORDER_Z=${BORDNEW_ARR[2]}
fi

echo "Using border operator size $BORDER_X x $BORDER_Y x $BORDER_Z"

# Check if border file exist already? where? (our dir), else call py step_bordercreate

# Call chain computer. if opencl is diabled, enable computation of output

# conversion to bin for py necessary!!!

# stl conversion

# merge files