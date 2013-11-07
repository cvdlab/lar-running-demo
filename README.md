lar-running-demo
=============

A demo beta software (set of scripts) to extract models from medical images.

Script has been tested on Ubuntu 12.04 LTS (x64).

MIT License.

Prerequisites
-------------
Every script check for its own prerequisites at the right time.
A list of them are:

* Bash
* Python (*PyPlasm, SciPy, NumPy, pypng, simplejson or json, requests, termcolor, matplotlib*)
* Java
* OpenCL
* Imagemagik
* dcm2pnm

startConversion.sh
-------------
It will extract all the possible models (the number depends of the quantized colors) automatically. Might take a while.

Input images allowed: *png, jpg, dcm*

Two type of executions:

* Interactive
* Command Line (use -h to know the exact paramaters)

startConversion-singleColor.sh
-------------
It will extract one of the possible model (the number depends of the quantized colors) automatically: it'll be choosen by selecting the index of the quantized color at runtime (mind that the quantized colors are always ordered in ascending order).

Input images allowed: *png, jpg, dcm*

Two type of executions:

* Interactive
* Command Line (use -h to know the exact paramaters)


visualize.sh
-------------
Given a Wavefront STL model (*obj*) it will show it using available on system visualizers.

Supported visualizers: *PyPlasm, MeshLab, Manta*

Two type of executions:

* Interactive
* Command Line (use -h to know the exact paramaters)
