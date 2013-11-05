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

colors = 2
log(1, ["colors = " + str(colors)]);

theColors = []
log(1, ["theColors = " + str(theColors)]);

DEBUG = False
log(1, ["DEBUG = " + str(DEBUG)]);

MAX_CHAINS = colors
log(1, ["MAX_CHAINS = " + str(MAX_CHAINS)]);

nx = ny = nz = 64
log(1, ["nx, ny, nz = " + str(nx) + "," + str(ny) + "," + str(nz)]);

imageDx = imageDy = imageDz = 64
log(1, ["imageDx, imageDy, imageDz = " + str(imageDx) + "," + str(imageDy) + "," + str(imageDz)]);

count = 0
log(1, ["count = " + str(count)]);

chunksize = nx * ny + nx * nz + ny * nz + 3 * nx * ny * nz
log(1, ["chunksize = " + str(chunksize)]);

# It is VERY important that the below parameter values correspond exactly to each other !!
beginImageStack = 0
log(1, ["beginImageStack = " + str(beginImageStack)]);

endImage = beginImageStack
log(1, ["endImage = " + str(endImage)]);

MAX_CHUNKS = 256 #1024
log(1, ["MAX_CHUNKS = " + str(MAX_CHUNKS)]);

imageHeight, imageWidth, imageDepth = 512,512,1024  # Dx, Dy, Dz
log(1, ["imageHeight, imageWidth, imageDepth = " + str(imageHeight) + "," + str(imageWidth) + "," + str(imageDepth)]);

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

'''
def invertPiece(nx,ny,nz):
	def invertIndex0(offset):
		a0, b0 = offset / nx, offset % nx
		a1, b1 = a0 / ny, a0 % ny
		a2, b2 = a1 / nz, a1 % nz
		return b0,b1,b2
	return invertIndex0
'''
# ------------------------------------------------------------
# Construction of vertex coordinates (nx * ny * nz)
# ------------------------------------------------------------

timer_start("V");

V = [[x,y,z] for z in range(nz+1) for y in range(ny+1) for x in range(nx+1) ]

timer_stop();
log(3, ["V = " + str(V)]);

# ------------------------------------------------------------
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
# Input from volume image
# ------------------------------------------------------------

# Loading the ∂3 operator from file
# ------------------------------------------------------------

timer_start("loading bordo3.json");
file = open('bordo3.json', 'r')
bordo3_json = json.load(file)
ROWCOUNT = bordo3_json['ROWCOUNT']
COLCOUNT = bordo3_json['COLCOUNT']
ROW = np.asarray(bordo3_json['ROW'], dtype=np.int32)
COL = np.asarray(bordo3_json['COL'], dtype=np.int32)
DATA = np.asarray(bordo3_json['DATA'], dtype=np.int8)
bordo3 = csr_matrix((DATA,COL,ROW),shape=(ROWCOUNT,COLCOUNT));
timer_stop();

Nx,Ny,Nz = imageHeight/imageDx, imageWidth/imageDx, imageDepth/imageDz
segFaces = set(["Fz0V","Fz1V","Fy0V","Fy1V","Fx0V","Fx1V"])
tempo_larboundary = 0;
pixelCalc, centroidsCalc = centroidcalc('SLICES/', 430, colors)
log(1, ["centroidsCalc = " + str(centroidsCalc)]);

for zBlock in range(imageDepth/imageDz):
	startImage = endImage
	endImage = startImage + imageDz
	xEnd, yEnd = 0,0
	theImage,colors,theColors = pngstack2array3d('SLICES/', startImage, endImage, colors, pixelCalc, centroidsCalc)
        log(1, ["theColors = "+ str(theColors)]);
	theColors = theColors.reshape(1,2)
	background = max(theColors[0])
	foreground = min(theColors[0])
	log(1, ["background = " + str(background)]);
        log(1, ["foreground = " + str(foreground)]);
	log(1, ["startImage = " + str(startImage)]);
        log(1, ["endImage = " + str(endImage)]);
	
	for xBlock in range(imageHeight/imageDx):
		
		for yBlock in range(imageWidth/imageDy):
			
			xStart, yStart = xBlock * imageDx, yBlock * imageDy
			xEnd, yEnd = xStart+imageDx, yStart+imageDy
			
			image = theImage[:, xStart:xEnd, yStart:yEnd]
			nz,nx,ny = image.shape

                        log(2, ["subimage count = " + str(count)]);
                        log(2, ["xStart, yStart = " + str(xStart) + ", " + str(yStart)]);
                        log(2, ["xEnd, yEnd = " + str(xEnd) + ", " + str(yEnd)]);
                        log(2, ["image.shape = " + str(image.shape)]);

			# ------------------------------------------------------------
			# Image elaboration  (chunck: 50 x 50 x 50)
			# ------------------------------------------------------------
			
			# Computation of (local) boundary to be removed by pieces
			# ------------------------------------------------------------
			"""
			pieceCoords = invertPiece(Nx,Ny,Nz)(count)
			if pieceCoords[2] == Nz-1: boundaryPlanes = ["Fz1V"]
			else:  boundaryPlanes = []

			if pieceCoords[0] == 0:  boundaryPlanes += ["Fx0V"]
			elif pieceCoords[0] == Nx-1:  boundaryPlanes += ["Fx1V"]
			if pieceCoords[1] == 0:  boundaryPlanes += ["Fy0V"]
			elif pieceCoords[1] == Ny-1:  boundaryPlanes += ["Fy1V"]
			if pieceCoords[2] == 0:  boundaryPlanes += ["Fz0V"]
			elif pieceCoords[2] == Nz-1:  boundaryPlanes += ["Fz1V"]
			
			if __name__=="__main__" and DEBUG == True:
				planesToRemove = list(segFaces.difference(boundaryPlanes))
				FVtoRemove = CAT(map(eval,planesToRemove))
			"""
			count += 1

			# Compute a quotient complex of chains with constant field
			# ------------------------------------------------------------

			chains3D_old = [];
			chains3D = np.zeros(nx*ny*nz,dtype=int32);
			zStart = startImage - beginImageStack;
			log(2, ["xStart, yStart, zStart = " + str(xStart) + ", " + str(yStart) + ", " + str(zStart)]);

			def addr(x,y,z): return x + (nx) * (y + (ny) * (z))
			
			for x in range(nx):
				for y in range(ny):
					for z in range(nz):
						if (image[x,y,z] == background):
							chains3D[addr(x,y,z)] = 1
							chains3D_old.append(addr(x,y,z))

			# Compute the boundary complex of the quotient cell
			# ------------------------------------------------------------

			timer_last = tm.time();
		        objectBoundaryChain = larBoundaryChain(bordo3,chains3D_old)
			# temp = objectBoundaryChain.toarray().astype(int32).flatten()
			# l = len(temp)
			# objectBoundaryChain_correct = scipy.sparse.csr_matrix((temp.reshape((l,1))))
			tempo_larboundary = tempo_larboundary + tm.time() - timer_last;
			print "Tempo larBoundaryChain() =", tempo_larboundary
		
			if ((xBlock == 0) and (yBlock == 0) and (zBlock == 0)):
				LISTA_VETTORI = np.array([chains3D], dtype=int32)
				LISTA_VETTORI2 = np.array([objectBoundaryChain.toarray().astype(int32).flatten()])
				LISTA_OFFSET =  np.array([[zStart,xStart,yStart]], dtype=int32)
			else:
				LISTA_VETTORI = np.append(LISTA_VETTORI, [chains3D], axis=0)
				LISTA_VETTORI2 = np.append(LISTA_VETTORI2, [objectBoundaryChain.toarray().astype(int32).flatten()], axis=0)
				LISTA_OFFSET =  np.append(LISTA_OFFSET, np.array([[zStart,xStart,yStart]], dtype=int32), axis=0)

			if count == MAX_CHUNKS: break
		if count == MAX_CHUNKS: break
	if count == MAX_CHUNKS: break

timer_start("selettori > file")
file = open('selettori.json', 'w')
json.dump({"lista_vettori":LISTA_VETTORI.tolist(), "lista_offset":LISTA_OFFSET.tolist()}, file, separators=(',',':'))
file.flush()
file.close()
timer_start("output > file")
file = open('output.json', 'w')
json.dump({"lista_vettori":LISTA_VETTORI2.tolist(), "lista_offset":LISTA_OFFSET.tolist()}, file, separators=(',',':'))
file.flush()
file.close()
timer_stop()
print "Tempo larBoundaryChain() =", tempo_larboundary

# Loading a quotient complex of chains with constant field
# ------------------------------------------------------------
'''
timer_start("loading selettori.json");
file = open('selettori.json', 'r')
selettori_json = json.load(file)
LISTA_VETTORI = np.asarray(selettori_json['lista_vettori'], dtype=np.int32)
LISTA_OFFSET = np.asarray(selettori_json['lista_offset'], dtype=np.int32)
timer_stop();
'''
# zStart, xStart, yStart = LISTA_OFFSET[1]

# chains3D = LISTA_VETTORI[1]

# Loading the boundary complex of the quotient cell
# ------------------------------------------------------------
'''
def loadjsonFile():
	timer_start("loading output.json");
	jsonFile = open('output.json', 'r')
	output_json = json.load(jsonFile)
	jsonFile.close()
	timer_stop();
	return output_json

def loadVectors(inputJson):
	timer_start("LISTA_VETTORI2");
	lvettori = np.asarray(inputJson['lista_vettori'], dtype=np.int32)
	timer_stop();

	timer_start("LISTA_OFFSET");
	loffset = np.asarray(inputJson['lista_offset'], dtype=np.int32)
	timer_stop();

	return [lvettori,loffset]

lstResult = loadVectors(loadjsonFile())
LISTA_VETTORI2 = lstResult[0]
LISTA_OFFSET = lstResult[1]

timer_start("LISTA_VETTORI2");
LISTA_VETTORI2 = np.asarray(output_json['lista_vettori'], dtype=np.int32)
timer_stop();

timer_start("LISTA_OFFSET");
LISTA_OFFSET = np.asarray(output_json['lista_offset'], dtype=np.int32)
timer_stop();

del output_json;
gc.collect();
output_json = 0;

gc.collect();
gc.collect();
gc.collect();
gc.collect();

# zStart, xStart, yStart = LISTA_OFFSET[1]

# l = len(LISTA_VETTORI2[1])
# objectBoundaryChain_correct = scipy.sparse.csr_matrix(LISTA_VETTORI2[1].reshape((l,1)))
'''
# ------------------------------------------------------------
# Visualize the generated model  
# ------------------------------------------------------------

out = []
file = open("output.bin", "rb")

for i in range(MAX_CHUNKS):

	count += 1

	zStart = struct.unpack('>I', file.read(4))[0]
	xStart = struct.unpack('>I', file.read(4))[0]
	yStart = struct.unpack('>I', file.read(4))[0]

	log(1, ["zStart, xStart, yStart = " + str(zStart) + "," + str(xStart) + "," + str(yStart)]);
#	zStart, xStart, yStart = LISTA_OFFSET[i].astype(float64)

	LISTA_VETTORI2 = np.zeros(chunksize,dtype=int32);

	temp = file.read(chunksize);

	timer_start("LISTA_VETTORI2 " + str(i));
	i = 0
	while (i < chunksize):
		if (temp[i] == '\x01'):
			LISTA_VETTORI2[i] = 1;
		i = i + 1;
	timer_stop();
	
	timer_start("objectBoundaryChain ");
	l = len(LISTA_VETTORI2)
	objectBoundaryChain = scipy.sparse.csr_matrix(LISTA_VETTORI2.reshape((l,1)))
	timer_stop();

	timer_start("csrChainToCellList " + str(i));
	b2cells = csrChainToCellList(objectBoundaryChain)
	timer_stop();

	timer_start("MKPOLS " + str(i));
	sup_cell_boundary = MKPOLS((V,[FV[f]  for f in b2cells]))
	timer_stop();

	timer_start("out " + str(i));
	if sup_cell_boundary != []:
		out += [T([1,2,3])([zStart,xStart,yStart])(STRUCT(sup_cell_boundary))]
	timer_stop();

	if count == MAX_CHUNKS:
		timer_start("VIEW(STRUCT(out))");
		VIEW(STRUCT(out))
		timer_stop();

file.close()

# ------------------------------------------------------------
# Remove the (local) boundary (shared with the piece boundary) from the quotient cell
# ------------------------------------------------------------
'''
cellIntersection = matrixProduct(csrCreate([FV[f] for f in b2cells]),csrCreate(FVtoRemove).T)
#print "\ncellIntersection =", cellIntersection
cooCellInt = cellIntersection.tocoo()
b2cells = [cooCellInt.row[k] for k,val in enumerate(cooCellInt.data) if val >= 4]
'''	
