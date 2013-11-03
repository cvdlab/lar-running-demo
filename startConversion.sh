#!/bin/bash
MYSELF=`basename $0`
WORKINDIR=$(pwd)
TMPNAME="tmp"
IMGDIRNAME="img"
BORDERDIRNAME="border"
COMPDIR="comp"
COMPDIRBIN="compbin"
STLDIR="stl"

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

# Generate tmp dir name
TMPDIRECTORY=$WORKINDIR/$TMPNAME/$(date | md5sum | head -c${1:-32})
echo "Using tmp directory $TMPDIRECTORY"

# Create clean dir
rm -fr $TMPDIRECTORY &> /dev/null
mkdir -p $TMPDIRECTORY &> /dev/null

if [ ! -d "$TMPDIRECTORY" ]; then
	echo "Could not create $TMPDIRECTORY. Aborting!"
	exit 1
fi

# Copy images to tmpimgdir
TMPIMGDIRECTORY=$TMPDIRECTORY/$IMGDIRNAME
mkdir -p $TMPIMGDIRECTORY &> /dev/null

if [ ! -d "$TMPIMGDIRECTORY" ]; then
	echo "Could not create $TMPIMGDIRECTORY Aborting!"
	exit 1
fi

cp $DIRINPUT/* $TMPIMGDIRECTORY &> /dev/null

# Convert image copied in $TMPIMGDIRECTORY
FIRSTFILE=$(ls $TMPIMGDIRECTORY | sort -n | head -1)
EXTFILE="${FIRSTFILE##*.}"
COUNTFILE=0
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

# Extract new bestfile name
BESTFILENAME=$BESTFILE.png
echo -n " done. Best image is now: $BESTFILE"
echo ""

# Image stats
BESTIMAGE_WIDTH=$(identify -format '%w' $TMPIMGDIRECTORY/$BESTFILENAME)
BESTIMAGE_HEIGHT=$(identify -format '%h' $TMPIMGDIRECTORY/$BESTFILENAME)
TOTALCOUNT=$(ls -1 $TMPIMGDIRECTORY | wc -l)

echo "Image sizes are $BESTIMAGE_WIDTH*$BESTIMAGE_HEIGHT*$TOTALCOUNT"
# Dealing with odd numbers is gruesome, they might even be prime
if [ $(( $TOTALCOUNT % 2 )) -ne 0 ]; then
	echo "Images are odd, adding one"
	convert -size $BESTIMAGE_WIDTH\x$BESTIMAGE_HEIGHT -colorspace gray xc:black $TMPIMGDIRECTORY/$COUNTFILE.png
	TOTALCOUNT=$((TOTALCOUNT + 1))
fi

# Guess a 2^x border dimension
BORDER_X=$(./sh/pow2test.sh $BESTIMAGE_WIDTH)
BORDER_Y=$(./sh/pow2test.sh $BESTIMAGE_HEIGHT)
BORDER_Z=$(./sh/pow2test.sh $TOTALCOUNT)
BORDER_ERR=0

# Might be erroneus
echo -n "Suggested border operator dim $BORDER_X x $BORDER_Y x $BORDER_Z "
if [ "$BORDER_X" -eq "0" ] || [ "$BORDER_Y" -eq "0" ] || [ "$BORDER_Z" -eq "0" ]; then
	echo -n "[might be erroneous]"
	BORDER_ERR=1
fi

# If erroneous force to input a new one
echo ""
if [ "$BORDER_ERR" -eq 1 ]; then
	echo -n "Enter new border operator dim [X*Y*Z and ENTER]: "
else
	echo -n "Enter new border operator dim [X*Y*Z and ENTER] [ENTER to skip]: "
fi
read BORDERNEW

# parse new border if necessary
if [ "$BORDER_ERR" -eq 1 ] || [ ! -z "$BORDERNEW" ]; then
	BORDNEW_ARR=($(echo $BORDERNEW | tr "*" "\n"))
	
	if [ ${#BORDNEW_ARR[@]} -ne 3 ]; then
		echo "Error in border dimensions. Aborting"
		exit 1
	fi
	
	BORDER_X=${BORDNEW_ARR[0]}
	BORDER_Y=${BORDNEW_ARR[1]}
	BORDER_Z=${BORDNEW_ARR[2]}
fi

echo "Using border operator size $BORDER_X x $BORDER_Y x $BORDER_Z"

# Check if border file exist already? where? (our dir), else call py step_bordercreate
BORDER_DIR=$WORKINDIR/$TMPNAME/$BORDERDIRNAME
BORDER_FILE="bordo3_$BORDER_X-$BORDER_Y-$BORDER_Z.json"
mkdir -p $BORDER_DIR &> /dev/null

if [ ! -r $BORDER_DIR/$BORDER_FILE ]; then
	echo -n "Generating border matrix ... "
	python ./py/computation/step_generatebordermtx.py -x $BORDER_X -y $BORDER_Y -z $BORDER_Z -o $BORDER_DIR &> /dev/null
	if [ $? -ne 0 ]; then
		echo -n "Error while generating $BORDER_DIR/$BORDER_FILE. Exiting."
		exit 1
	else
		echo -n "done!"
	fi
else
	echo -n "Using precalculated matrix."
fi
echo ""


# Call chain computer. if opencl is diabled, enable computation of output
COMPUTATION_DIR=$TMPDIRECTORY/$COMPDIR
mkdir -p $COMPUTATION_DIR &> /dev/null

COMPUTATION_DIR_BIN=$TMPDIRECTORY/$COMPDIRBIN
mkdir -p $COMPUTATION_DIR_BIN &> /dev/null

if [ $OPENCL -eq 1 ]; then
	python ./py/computation/step_calcchains.py -b $BORDER_DIR/$BORDER_FILE -x $BORDER_X -y $BORDER_Y -z $BORDER_Z -i $TMPIMGDIRECTORY -c $COLORS -q $BESTFILE -o $COMPUTATION_DIR &> /dev/null
	if [ $? -ne 0 ]; then
		echo "Error while computing chains"
		exit 1
	fi	
	# Call OpenCL JAR
	# here use updated jar that outputs directly in binary in $COMPUTATION_DIR_BIN
else
	python ./py/computation/step_calcchains.py -r -b $BORDER_DIR/$BORDER_FILE -x $BORDER_X -y $BORDER_Y -z $BORDER_Z -i $TMPIMGDIRECTORY -c $COLORS -q $BESTFILE -o $COMPUTATION_DIR &> /dev/null
	if [ $? -ne 0 ]; then
		echo "Error while computing output chains"
		exit 1
	fi
	#Convert output-*.json to .bin
	for genOut in $(ls $COMPUTATION_DIR/output); do
		python ./py/computation/step_convoutput.py -i $COMPUTATION_DIR/$genOut -o $COMPUTATION_DIR_BIN &> /dev/null
		if [ $? -ne 0 ]; then
			echo "Error while converting output to binary: $genOut"
			exit 1
		fi
	done
fi

# stl conversion and merge
STL_DIR=$TMPDIRECTORY/$STLDIR
mkdir -p $STL_DIR &> /dev/null
COUNTFILE=1
for binOut in $(ls $COMPUTATION_DIR_BIN); do
	python ./py/computation/step_triangularmesh.py -x $BORDER_X -y $BORDER_y -z $BORDER_Z -i $COMPUTATION_DIR_BIN/$binOut -o $STL_DIR &> /dev/null
	if [ $? -ne 0 ]; then
		echo "Error while converting output to binary: $genOut"
		exit 1
	fi
	
	STL_OUT_FILE=$STL_DIR/model-$COUNTFILE.obj
	touch $STL_OUT_FILE
	for stlFile in $(ls $STL_DIR/*.stl); do
		cat $STL_DIR/$stlFile >> $STL_OUT_FILE
		rm $STL_DIR/$stlFile
	done
	
	echo "Model $STL_OUT_FILE ready."
	COUNTFILE=$((COUNTFILE + 1))
done