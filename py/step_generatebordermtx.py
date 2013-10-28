# -*- coding: utf-8 -*-

from lar import *
from scipy import *
import json
import scipy
import numpy as np
import time as tm
import gc
from pngstack2array3d import *
import struct
import sys

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

logging_level = 2; 

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
        print "Timer start:", s;
    timer_last = tm.time();

def timer_stop():

    global timer_last;
    if __name__=="__main__" and timer == 1:   
        print "Timer stop :", tm.time() - timer_last;

# ------------------------------------------------------------
# Configuration parameters
# ------------------------------------------------------------

DEBUG = False
log(1, ["DEBUG = " + str(DEBUG)]);

nx = ny = nz = int(sys.argv[1])
log(1, ["nx, ny, nz = " + str(nx) + "," + str(ny) + "," + str(nz)]);

# ------------------------------------------------------------
# Utility toolbox
# ------------------------------------------------------------

def ind(x,y,z): return x + (nx+1) * (y + (ny+1) * (z))

def invertIndex(nx,ny,nz):
	nx,ny,nz = nx+1,ny+1,nz+1
	def invertIndex0(offset):
		a0, b0 = offset / nx, offset % nx
		a1, b1 = a0 / ny, a0 % ny
		a2, b2 = a1 / nz, a1 % nz
		return b0,b1,b2
	return invertIndex0

# ------------------------------------------------------------
# Computation of d-chain generators (d-cells)
# ------------------------------------------------------------

# Cubic cell complex
# ------------------------------------------------------------

timer_start("the3Dcell");

def the3Dcell(coords):
	x,y,z = coords
	return [ind(x,y,z),ind(x+1,y,z),ind(x,y+1,z),ind(x,y,z+1),ind(x+1,y+1,z),
			ind(x+1,y,z+1),ind(x,y+1,z+1),ind(x+1,y+1,z+1)]
timer_stop();

# Construction of vertex coordinates (nx * ny * nz)
# ------------------------------------------------------------

timer_start("V");

V = [[x,y,z] for z in range(nz+1) for y in range(ny+1) for x in range(nx+1) ]

timer_stop();
log(3, ["V = " + str(V)]);

# Construction of CV relation (nx * ny * nz)
# ------------------------------------------------------------

timer_start("CV");

CV = [the3Dcell([x,y,z]) for z in range(nz) for y in range(ny) for x in range(nx)]

timer_stop();
log(3, ["CV = " + str(CV)]);

if __name__=="__main__" and DEBUG == True:
	hpc = EXPLODE(1.2,1.2,1.2)(MKPOLS((V,CV[:500]+CV[-500:])))
	box = SKELETON(1)(BOX([1,2,3])(hpc))
	VIEW(STRUCT([box,hpc]))

# Construction of FV relation (nx * ny * nz)
# ------------------------------------------------------------

FV = []

timer_start("v2coords");

v2coords = invertIndex(nx,ny,nz)

timer_stop();

timer_start("h");

for h in range(len(V)):
	x,y,z = v2coords(h)
	if (x < nx) and (y < ny): FV.append([h,ind(x+1,y,z),ind(x,y+1,z),ind(x+1,y+1,z)])
	if (x < nx) and (z < nz): FV.append([h,ind(x+1,y,z),ind(x,y,z+1),ind(x+1,y,z+1)])
	if (y < ny) and (z < nz): FV.append([h,ind(x,y+1,z),ind(x,y,z+1),ind(x,y+1,z+1)])

timer_stop();
log(3, ["FV = " + str(FV)]);
'''
if __name__=="__main__" and DEBUG == True:
	hpc = EXPLODE(1.2,1.2,1.2)(MKPOLS((V,FV[:500]+FV[-500:])))
	box = SKELETON(1)(BOX([1,2,3])(hpc))
	VIEW(STRUCT([box,hpc]))
'''
# ------------------------------------------------------------
# Computation of boundary operators (∂3 and ∂2s)
# ------------------------------------------------------------

# Computation of the 2D boundary complex of the image space 
# ------------------------------------------------------------
'''
Fx0V, Ex0V = [],[]  # x == 0
Fx1V, Ex1V = [],[]  # x == nx-1
Fy0V, Ey0V = [],[]  # y == 0
Fy1V, Ey1V = [],[]  # y == ny-1
Fz0V, Ez0V = [],[]  # z == 0
Fz1V, Ez1V = [],[]  # z == nz-1
v2coords = invertIndex(nx,ny,nz)
for h in range(len(V)):
	x,y,z = v2coords(h)
	if (z == 0):
		if x < nx: Ez0V.append([h,ind(x+1,y,z)])
		if y < ny: Ez0V.append([h,ind(x,y+1,z)])
		if (x < nx) and (y < ny):
			Fz0V.append([h,ind(x+1,y,z),ind(x,y+1,z),ind(x+1,y+1,z)])
	elif (z == nz):
		if x < nx: Ez1V.append([h,ind(x+1,y,z)])
		if y < ny: Ez1V.append([h,ind(x,y+1,z)])
		if (x < nx)  and (y < ny):
			Fz1V.append([h,ind(x+1,y,z),ind(x,y+1,z),ind(x+1,y+1,z)])

	if (y == 0):
		if x < nx: Ey0V.append([h,ind(x+1,y,z)])
		if z < nz: Ey0V.append([h,ind(x,y,z+1)])
		if (x < nx) and (z < nz):
			Fy0V.append([h,ind(x+1,y,z),ind(x,y,z+1),ind(x+1,y,z+1)])
	elif (y == ny):
		if x < nx: Ey1V.append([h,ind(x+1,y,z)])
		if z < nz: Ey1V.append([h,ind(x,y,z+1)])
		if (x < nx) and (z < nz):
			Fy1V.append([h,ind(x+1,y,z),ind(x,y,z+1),ind(x+1,y,z+1)])

	if (x == 0):
		if y < ny: Ex0V.append([h,ind(x,y+1,z)])
		if z < nz: Ex0V.append([h,ind(x,y,z+1)])
		if (y < ny) and (z < nz):
			Fx0V.append([h,ind(x,y+1,z),ind(x,y,z+1),ind(x,y+1,z+1)])
	elif (x == nx):
		if y < ny: Ex1V.append([h,ind(x,y+1,z)])
		if z < nz: Ex1V.append([h,ind(x,y,z+1)])
		if (y < ny) and (z < nz):
			Fx1V.append([h,ind(x,y+1,z),ind(x,y,z+1),ind(x,y+1,z+1)])

FbV = Fz0V+Fz1V+Fy0V+Fy1V+Fx0V+Fx1V
EbV = Ez0V+Ez1V+Ey0V+Ey1V+Ex0V+Ex1V

if __name__=="__main__" and DEBUG == True:
	hpc = EXPLODE(1.2,1.2,1.2)(MKPOLS((V,FbV)))
	VIEW(hpc)
	hpc = EXPLODE(1.2,1.2,1.2)(MKPOLS((V,EbV)))
	VIEW(hpc)
'''	
# Computation of the ∂2 operator on the boundary space
# ------------------------------------------------------------
'''
timer_start("partial_2_b");
#partial_2_b = larBoundary(EbV,FbV)
timer_stop();
'''
# Computation of ∂3 operator on the image space
# ------------------------------------------------------------

timer_start("larBoundary > bordo3");
bordo3 = larBoundary(FV,CV)
timer_stop();
log(3, ["bordo3 = " + str(bordo3)])

timer_start("bordo3 > file");
ROWCOUNT = bordo3.shape[0]
COLCOUNT = bordo3.shape[1]
ROW = bordo3.indptr.tolist()
COL = bordo3.indices.tolist()
DATA = bordo3.data.tolist()
file = open('bordo3.json', 'w')
json.dump({"ROWCOUNT":ROWCOUNT, "COLCOUNT":COLCOUNT, "ROW":ROW, "COL":COL, "DATA":DATA }, file, separators=(',',':'))
file.flush();
file.close();
timer_stop();

