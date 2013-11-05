#!/bin/sh

MESHLAB=$(which meshlab)
MANTA=$(which manta)

echo "*********************"
echo "Visualize model"
echo "*********************"

echo -n "Enter OBJ model filename (with path) [ENTER]: "
read MODELINPUT

if [ -z "$MODELINPUT" ] || [ ! -r "$MODELINPUT" ]; then
	echo "Wrong file $MODELINPUT"
	exit 1
fi

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
    $MANTA -np 2 -ui X -scene "lib/libscene_triangleSceneViewer( -model $MODELINPUT -DynBVH -smoothAnimation -overrideMatl eyelight -ambient constant )"
    ;;
*)
    echo ""
    ;;
esac