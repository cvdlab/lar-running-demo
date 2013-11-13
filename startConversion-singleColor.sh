#!/bin/bash
DATE=`date +%Y-%m-%d`
MYSELF=`basename $0`
WORKINDIR=$(pwd)
JARNAME="lar-javacl.jar"
PYBIN=$(which python)
JAVABIN=$(which java)
#
TMPNAME="tmp"
IMGDIRNAME="img"
BORDERDIRNAME="border"
COMPDIR="comp"
COMPDIRBIN="compbin"
STLDIR="stl"
# ****
chmod 0755 ./sh/*.sh
# ****
# LOGGING
LOGDIR=$WORKINDIR/log
LOGFILE=$LOGDIR/executionLog-$DATE
mkdir -p $LOGDIR
touch $LOGFILE
######

show_help() {
	echo "Either run without args or with"
	echo "To use args enable it with -u"
	echo "-d <input images>	: Directory containing input images"
	echo "-f <best image>		: Image to quantize on"
	echo "-q <colors>		: Number of colors to quantize (min 2)"
	echo "-r <colorIdx>		: Color to extract (0 to <colors - 1>)"
	echo "-c					: Use OpenCL"
}

echo "==================="
echo "LAR Model extractor"
echo "==================="

USECMDLINE=0
OPTIND=1 # Reset is necessary if getopts was used previously in the script.  It is a good idea to make this local in a function.
while getopts "h?cud:f:q:r:" opt; do
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
		r)  COLOR_SEL=$OPTARG
			;;
		c)  OPENCL="y"
			;;
	esac
done
shift $((OPTIND-1)) # Shift off the options and optional --.

echo "** Checking Basic Prerequisites **"

sh ./sh/prerequites-python.sh
if [ $? -ne 0 ]; then
	echo "Missing prerequisites, install them (check output)."
	exit 1
fi

sh ./sh/prerequites-imagick.sh
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
	echo -n "Color to extract the model (0 to colors) [ENTER]: "
	read COLOR_SEL	
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

if [ -z "$COLOR_SEL" ] || [ -z "${COLOR_SEL##*[!0-9]*}" ] || [ "$COLOR_SEL" -ge "$COLORS" ]; then
	echo "Wrong selected color index $COLOR_SEL"
	exit 1
fi

if [ -z "$OPENCL" ] || [ "$OPENCL" != "y" ]; then
	echo "Not using OpenCL"
	OPENCL=0
else 
	echo "Using OpenCL for available operations"
	OPENCL=1
	
	# Check for Java now
	sh ./sh/prerequites-java.sh
	if [ $? -ne 0 ]; then
		echo "Missing prerequisites, install them (check output)."
		exit 1
	fi
fi

# Empty line
echo ""

echo "Will try to extract model from $DIRINPUT/ using color quantization ($COLORS on color $COLOR_SEL)"
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
rm -fr $TMPDIRECTORY >> $LOGFILE 2>&1
mkdir -p $TMPDIRECTORY >> $LOGFILE 2>&1

if [ ! -d "$TMPDIRECTORY" ]; then
	echo "Could not create $TMPDIRECTORY. Aborting!"
	exit 1
fi

# Copy images to tmpimgdir
TMPIMGDIRECTORY=$TMPDIRECTORY/$IMGDIRNAME
mkdir -p $TMPIMGDIRECTORY >> $LOGFILE 2>&1

if [ ! -d "$TMPIMGDIRECTORY" ]; then
	echo "Could not create $TMPIMGDIRECTORY Aborting!"
	exit 1
fi

cp "$DIRINPUT"/* $TMPIMGDIRECTORY >> $LOGFILE 2>&1

# Convert image copied in $TMPIMGDIRECTORY
FIRSTFILE=$(ls $TMPIMGDIRECTORY | sort -n | head -1)
EXTFILE="${FIRSTFILE##*.}"
COUNTFILE=0
BESTFILE=$STARTFILE

echo -n "Converting input images..."
if [ "$EXTFILE" == "png" ] || [ "$EXTFILE" == "jpg" ]; then
	# Convert
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
	# Check for DCM now
	sh ./sh/prerequites-dcm.sh
	if [ $? -ne 0 ]; then
		echo "Missing prerequisites, install them (check output)."
		exit 1
	fi
	# Convert
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
	rm -fr $TMPDIRECTORY >> $LOGFILE 2>&1
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
mkdir -p $BORDER_DIR >> $LOGFILE 2>&1

if [ ! -r $BORDER_DIR/$BORDER_FILE ]; then
	echo -n "Generating border matrix ... "
	$PYBIN ./py/computation/step_generatebordermtx.py -x $BORDER_X -y $BORDER_Y -z $BORDER_Z -o $BORDER_DIR >> $LOGFILE 2>&1
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
mkdir -p $COMPUTATION_DIR >> $LOGFILE 2>&1

COMPUTATION_DIR_BIN=$TMPDIRECTORY/$COMPDIRBIN
mkdir -p $COMPUTATION_DIR_BIN >> $LOGFILE 2>&1

if [ $OPENCL -eq 1 ]; then
	echo -n "Computing input binary chains... "
	CHAINCURR=$COLOR_SEL
	#while [ $CHAINCURR -lt $COLORS ]; do
		$PYBIN ./py/computation/step_calcchains_serial_tobinary_filter.py -b $BORDER_DIR/$BORDER_FILE -x $BORDER_X -y $BORDER_Y -z $BORDER_Z -i $TMPIMGDIRECTORY -c $COLORS -d $CHAINCURR -q $BESTFILE -o $COMPUTATION_DIR >> $LOGFILE 2>&1
		if [ $? -ne 0 ]; then
			echo "Error while computing output chains"
			exit 1
		fi
	#	CHAINCURR=$((CHAINCURR + 1))
	# done
	echo -n "done!"
	echo ""	
	# Call OpenCL JAR
	# here use updated jar that outputs directly in binary in $COMPUTATION_DIR_BIN
	echo -n "Computing output binary chains... "
	for selettoreFile in $COMPUTATION_DIR/selettori-*.bin; do
		selettoreId=$(basename $selettoreFile | cut -d'.' -f1 | cut -d'-' -f2)
		LD_PRELOAD=$JAVA_HOME/jre/lib/amd64/libjsig.so $JAVABIN -d64 -Xcheck:jni -Xmx16G -XX:MaxPermSize=4G -XX:PermSize=512M -jar ./java/$JARNAME -b $BORDER_DIR/$BORDER_FILE -v $selettoreFile -y -o $COMPUTATION_DIR_BIN/output-$selettoreId.bin
		if [ $? -ne 0 ]; then
			echo "Error while computing output binary chains"
			exit 1
		fi
	done
	echo -n "done!"
	echo ""	
else
	echo -n "Computing output binary chains... "
	CHAINCURR=$COLOR_SEL
	#while [ $CHAINCURR -lt $COLORS ]; do
		$PYBIN ./py/computation/step_calcchains_serial_tobinary_filter.py -r -b $BORDER_DIR/$BORDER_FILE -x $BORDER_X -y $BORDER_Y -z $BORDER_Z -i $TMPIMGDIRECTORY -c $COLORS -d $CHAINCURR -q $BESTFILE -o $COMPUTATION_DIR_BIN >> $LOGFILE 2>&1
		if [ $? -ne 0 ]; then
			echo "Error while computing output chains"
			exit 1
		fi
	#	CHAINCURR=$((CHAINCURR + 1))
	#done
	echo -n "done!"
	echo ""
fi

# stl conversion and merge
STL_DIR=$TMPDIRECTORY/$STLDIR
mkdir -p $STL_DIR >> $LOGFILE 2>&1

echo "Converting to wavefront model ... "
for binOut in $COMPUTATION_DIR_BIN/output-*.bin; do
	$PYBIN ./py/computation/step_triangularmesh.py -x $BORDER_X -y $BORDER_Y -z $BORDER_Z -i $binOut -o $STL_DIR >> $LOGFILE 2>&1
	if [ $? -ne 0 ]; then
		echo "Error while converting output to binary: $binOut"
		exit 1
	fi
	
	outputId=$(basename $binOut | cut -d'.' -f1 | cut -d'-' -f2)
	STL_OUT_FILE=$STL_DIR/model-$outputId.obj
	touch $STL_OUT_FILE
	for stlFile in $STL_DIR/output-*-$outputId.stl; do
		cat $stlFile >> $STL_OUT_FILE
		rm $stlFile
	done
	
	echo "Wavefront model $STL_OUT_FILE ready."
done