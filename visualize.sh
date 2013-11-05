#!/bin/bash

MESHLAB=$(which meshlab)
MANTA=$(which manta)
# ****
chmod 0755 ./sh/*.sh
# ****

show_help() {
	echo "Either run without args or with"
	echo "To use args enable it with -u"
	echo "-f <input model>	: Obj input model"
}

USECMDLINE=0
OPTIND=1 # Reset is necessary if getopts was used previously in the script.  It is a good idea to make this local in a function.
while getopts "h?uf:" opt; do
	case "$opt" in
		h|\?)
			show_help
			exit 0
			;;
		u)  USECMDLINE=1
			;;
		f)  MODELINPUT=$OPTARG
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

echo "*********************"
echo "Visualize model"
echo "*********************"

if [ "$USECMDLINE" -eq "0" ]; then
	echo -n "Enter OBJ model filename (with path) [ENTER]: "
	read MODELINPUT
fi

if [ -z "$MODELINPUT" ] || [ ! -r "$MODELINPUT" ]; then
	echo "Wrong file $MODELINPUT"
	exit 1
fi
MODELINPUT=$(echo $MODELINPUT | sed 's/ /\\ /g')

VISUALIZE=1

echo "Load with:"
echo "$VISUALIZE -> PyPlasm"
if [ ! -z "$MESHLAB" ]; then
	VISUALIZE=$((VISUALIZE + 1))
	echo "$VISUALIZE -> Meshlab"
fi
if [ ! -z "$MANTA" ]; then
	VISUALIZE=$((VISUALIZE + 1))
	echo "$VISUALIZE -> Manta"
fi
echo -n "Select a number [max $VISUALIZE]: "
read -n 1 VIS_SELECT

echo ""
if [ -z "$VIS_SELECT" ] || [ -z "${VIS_SELECT##*[!0-9]*}" ] || [ "$VIS_SELECT" -gt "$VISUALIZE" ]; then
	echo "Wrong selection $VIS_SELECT"
	exit 1
fi

case "$VIS_SELECT" in
"1")
    python ./py/computation/step_loadmodel.py -i $MODELINPUT
    ;;
"2")
    $MESHLAB $MODELINPUT
    ;;
"3")
	MANTADIR=$(dirname ${MANTA})
	cd $MANTADIR
	cd ..
    bin/manta -np 2 -ui X -scene "lib/libscene_triangleSceneViewer( -model $MODELINPUT -DynBVH -smoothAnimation -overrideMatl eyelight -ambient constant )"
    ;;
*)
    echo ""
    ;;
esac