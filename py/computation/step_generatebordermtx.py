# -*- coding: utf-8 -*-

from lar import *
from scipy import *
import json
import scipy
import numpy as np
import time as tm
import gc
import struct
import sys
import getopt, sys

# ------------------------------------------------------------
# Bash command
#
# $ python bordo3.py 64
#
# to get a bordo3.json of a 64x64x64 block
#
# ------------------------------------------------------------

# ------------------------------------------------------------
# Logging & Timer 
# ------------------------------------------------------------

logging_level = 0; 

# 0 = no_logging
# 1 = few details
# 2 = many details
# 3 = many many details

def log(n, l):

    if __name__=="__main__" and n <= logging_level:
        for s in l:
            print "Log:", s;

timer = 1;

timer_last =  tm.time()

def timer_start(s):

    global timer_last;
    if __name__=="__main__" and timer == 1:   
        log(3, ["Timer start:" + s]);
    timer_last = tm.time();

def timer_stop():

    global timer_last;
    if __name__=="__main__" and timer == 1:   
        log(3, ["Timer stop :" + str(tm.time() - timer_last)]);

# ------------------------------------------------------------
# Utility toolbox
# ------------------------------------------------------------

# ------------------------------------------------------------
# Computation of d-chain generators (d-cells)
# ------------------------------------------------------------

# Cubic cell complex
# ------------------------------------------------------------


# Computation of ∂3 operator on the image space
# ------------------------------------------------------------

def computeBordo3(FV,CV,inputFile='bordo3.json'):
	log(1, ["bordo3 = Starting"])
	bordo3 = larBoundary(FV,CV)
	log(3, ["bordo3 = " + str(bordo3)])
	log(1, ["bordo3 = Done"])

	ROWCOUNT = bordo3.shape[0]
	COLCOUNT = bordo3.shape[1]
	ROW = bordo3.indptr.tolist()
	COL = bordo3.indices.tolist()
	DATA = bordo3.data.tolist()

	with open(inputFile, "w") as file:
		json.dump({"ROWCOUNT":ROWCOUNT, "COLCOUNT":COLCOUNT, "ROW":ROW, "COL":COL, "DATA":DATA }, file, separators=(',',':'))
		file.flush();

def main(argv):
	ARGS_STRING = 'Args: -x <borderX> -y <borderY> -z <borderZ> -o <outputdir>'

	try:
		opts, args = getopt.getopt(argv,"o:x:y:z:")
	except getopt.GetoptError:
		print ARGS_STRING
		sys.exit(2)
	
	mandatory = 2
	#Files
	DIR_OUT = ''
	
	for opt, arg in opts:
		if opt == '-x':
			nx = ny = nz = int(arg)
			mandatory = mandatory - 1
		elif opt == '-y':
			ny = nz = int(arg)
		elif opt == '-z':
			nz = int(arg)
		elif opt == '-o':
			DIR_OUT = arg
			mandatory = mandatory - 1
			
	if mandatory != 0:
		print 'Not all arguments where given'
		print ARGS_STRING
		sys.exit(2)
		
	log(1, ["nx, ny, nz = " + str(nx) + "," + str(ny) + "," + str(nz)]);
	
	
	def ind(x,y,z): return x + (nx+1) * (y + (ny+1) * (z))

	def invertIndex(nx,ny,nz):
		nx,ny,nz = nx+1,ny+1,nz+1
		def invertIndex0(offset):
			a0, b0 = offset / nx, offset % nx
			a1, b1 = a0 / ny, a0 % ny
			a2, b2 = a1 / nz, a1 % nz
			return b0,b1,b2
		return invertIndex0
		
	def the3Dcell(coords):
		x,y,z = coords
		return [ind(x,y,z),ind(x+1,y,z),ind(x,y+1,z),ind(x,y,z+1),ind(x+1,y+1,z),
				ind(x+1,y,z+1),ind(x,y+1,z+1),ind(x+1,y+1,z+1)]	
	
	# Construction of vertex coordinates (nx * ny * nz)
	# ------------------------------------------------------------

	V = [[x,y,z] for z in range(nz+1) for y in range(ny+1) for x in range(nx+1) ]

	log(3, ["V = " + str(V)]);

	# Construction of CV relation (nx * ny * nz)
	# ------------------------------------------------------------

	CV = [the3Dcell([x,y,z]) for z in range(nz) for y in range(ny) for x in range(nx)]

	log(3, ["CV = " + str(CV)]);

	# Construction of FV relation (nx * ny * nz)
	# ------------------------------------------------------------

	FV = []

	v2coords = invertIndex(nx,ny,nz)

	for h in range(len(V)):
		x,y,z = v2coords(h)
		if (x < nx) and (y < ny): FV.append([h,ind(x+1,y,z),ind(x,y+1,z),ind(x+1,y+1,z)])
		if (x < nx) and (z < nz): FV.append([h,ind(x+1,y,z),ind(x,y,z+1),ind(x+1,y,z+1)])
		if (y < ny) and (z < nz): FV.append([h,ind(x,y+1,z),ind(x,y,z+1),ind(x,y+1,z+1)])

	log(3, ["FV = " + str(FV)]);
	
	fileName = DIR_OUT+'/bordo3_'+str(nx)+'-'+str(ny)+'-'+str(nz)+'.json'
	
	try:
		computeBordo3(FV,CV,fileName)
	except:
		print "Unexpected error:", sys.exc_info()[0]
		sys.exit(2)

if __name__ == "__main__":
   main(sys.argv[1:])