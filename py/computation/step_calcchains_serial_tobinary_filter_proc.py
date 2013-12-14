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
import getopt, sys
import traceback
#
import matplotlib.pyplot as plt
# threading
import multiprocessing
from multiprocessing import Process, Value, Lock
from Queue import Queue
# cython stuf. not used now
import pyximport; pyximport.install()
import calc_chains_helper as cch

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

# ------------------------------------------------------------
# Configuration parameters
# ------------------------------------------------------------

PNG_EXTENSION = ".png"
BIN_EXTENSION = ".bin"

# ------------------------------------------------------------
# Utility toolbox
# ------------------------------------------------------------

def invertIndex(nx,ny,nz):
	nx,ny,nz = nx+1,ny+1,nz+1
	def invertIndex0(offset):
		a0, b0 = offset / nx, offset % nx
		a1, b1 = a0 / ny, a0 % ny
		a2, b2 = a1 / nz, a1 % nz
		return b0,b1,b2
	return invertIndex0

def countFilesInADir(directory):
	return len(os.walk(directory).next()[2])
	
def isArrayEmpty(arr):
	return all(e == 0 for e in arr)
	
# ------------------------------------------------------------
def writeOffsetToFile(file, offsetCurr):
	file.write( struct.pack('>I', offsetCurr[0]) )
	file.write( struct.pack('>I', offsetCurr[1]) )
	file.write( struct.pack('>I', offsetCurr[2]) )
# ------------------------------------------------------------

def computeChainsThread(startImage,endImage,imageHeight,imageWidth, imageDx,imageDy,imageDz, Nx,Ny,Nz, calculateout,BORDER_FILE, colors,pixelCalc,centroidsCalc, colorIdx, imageDir, DIR_O):
	log(2, [ "Working task: " +str(startImage) + "-" + str(endImage) + " [" + str( imageHeight) + "-" + str( imageWidth ) + "-" + str(imageDx) + "-" + str( imageDy) + "-" + str (imageDz) + "]" ])
	
	bordo3 = None
	if (calculateout == True):
		with open(BORDER_FILE, "r") as file:
			bordo3_json = json.load(file)
			ROWCOUNT = bordo3_json['ROWCOUNT']
			COLCOUNT = bordo3_json['COLCOUNT']
			ROW = np.asarray(bordo3_json['ROW'], dtype=np.int32)
			COL = np.asarray(bordo3_json['COL'], dtype=np.int32)
			DATA = np.asarray(bordo3_json['DATA'], dtype=np.int8)
			bordo3 = csr_matrix((DATA,COL,ROW),shape=(ROWCOUNT,COLCOUNT));

	xEnd, yEnd = 0,0
	beginImageStack = 0
	saveTheColors = centroidsCalc
	saveTheColors = np.array( sorted(saveTheColors.reshape(1,colors)[0]), dtype=np.int )

	fileName = "pselettori-"
	if (calculateout == True):
		fileName = "poutput-"
	fileName = fileName + str(startImage) + "_" + str(endImage) + "-"

	returnProcess = 0

	try:
		fileToWrite = open(DIR_O+'/'+fileName+str(saveTheColors[colorIdx])+BIN_EXTENSION, "wb")
		try:
			log(2, [ "Working task: " +str(startImage) + "-" + str(endImage) + " [loading colors]" ])
			theImage,colors,theColors = pngstack2array3d(imageDir, startImage, endImage, colors, pixelCalc, centroidsCalc)		
			# theColors = theColors.reshape(1,colors)
			# if (sorted(theColors[0]) != saveTheColors):
			#	log(1, [ "Error: colors have changed"] )
			#	sys.exit(2)
			
			log(2, [ "Working task: " +str(startImage) + "-" + str(endImage) + " [comp loop]" ])
			for xBlock in xrange(imageHeight/imageDx):
				# print "Working task: " +str(startImage) + "-" + str(endImage) + " [Xblock]"
				for yBlock in xrange(imageWidth/imageDy):
					# print "Working task: " +str(startImage) + "-" + str(endImage) + " [Yblock]"
					xStart, yStart = xBlock * imageDx, yBlock * imageDy
					xEnd, yEnd = xStart+imageDx, yStart+imageDy
								
					image = theImage[:, xStart:xEnd, yStart:yEnd]
					nz,nx,ny = image.shape

					# Compute a quotient complex of chains with constant field
					# ------------------------------------------------------------

					chains3D_old = [];
					chains3D = None
					hasSomeOne = False
					if (calculateout != True):
						chains3D = np.zeros(nx*ny*nz, dtype=np.int32)
								
					zStart = startImage - beginImageStack;

					if (calculateout == True):
						chains3D_old = cch.setList(nx,ny,nz, colorIdx, image,saveTheColors)
					else:
						hasSomeOne,chains3D = cch.setListNP(nx,ny,nz, colorIdx, image,saveTheColors)
			
					# print "Working task: " +str(startImage) + "-" + str(endImage) + " [hasSomeOne: " + str(hasSomeOne) +"]"
							
					# Compute the boundary complex of the quotient cell
					# ------------------------------------------------------------
					objectBoundaryChain = None
					if (calculateout == True) and (len(chains3D_old) > 0):
						objectBoundaryChain = larBoundaryChain(bordo3,chains3D_old)
							
					# Save
					if (calculateout == True):
						if (objectBoundaryChain != None):
							writeOffsetToFile( fileToWrite, np.array([zStart,xStart,yStart], dtype=int32) )
							fileToWrite.write( bytearray( np.array(objectBoundaryChain.toarray().astype('b').flatten()) ) )
					else:
						if (hasSomeOne != False):
							writeOffsetToFile( fileToWrite, np.array([zStart,xStart,yStart], dtype=int32) )
							fileToWrite.write( bytearray( np.array(chains3D, dtype=np.dtype('b')) ) )
		except:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
			log(1, [ "Error: " + ''.join('!! ' + line for line in lines) ])  # Log it or whatever here
			returnProcess = 2
		finally:
			fileToWrite.close()
		# -------------------------------------------------------------------------
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
		log(1, [ "Error: " + ''.join('!! ' + line for line in lines) ])  # Log it or whatever here
		returnProcess = 2

	return returnProcess

processRes = []
def collectResult(resData):
	processRes.append(resData)

def startComputeChains(imageHeight,imageWidth,imageDepth, imageDx,imageDy,imageDz, Nx,Ny,Nz, calculateout,BORDER_FILE, colors,pixelCalc,centroidsCalc, colorIdx,INPUT_DIR,DIR_O):
	beginImageStack = 0
	endImage = beginImageStack
	
	saveTheColors = centroidsCalc
	log(2, [ centroidsCalc ])
	saveTheColors = np.array( sorted(saveTheColors.reshape(1,colors)[0]), dtype=np.int )
	log(2, [ saveTheColors ])
	# print str(imageHeight) + '-' + str(imageWidth) + '-' + str(imageDepth)
	# print str(imageDx) + '-' + str(imageDy) + '-' + str(imageDz)
	# print str(Nx) + '-' + str(Ny) + '-' + str(Nz)
	returnValue = 2

	processPool = max(1, multiprocessing.cpu_count()/2)
	log(2, [ "Starting pool with: " + str(processPool) ])

	try:
		pool = multiprocessing.Pool(processPool)
		log(2, [ 'Start pool' ])
		
		for j in xrange(imageDepth/imageDz):
			startImage = endImage
			endImage = startImage + imageDz
			log(2, [ "Added task: " + str(j) + " -- (" + str(startImage) + "," + str(endImage) + ")" ])
			pool.apply_async(computeChainsThread, args = (startImage,endImage,imageHeight,imageWidth, imageDx,imageDy,imageDz, Nx,Ny,Nz, calculateout,BORDER_FILE, colors,pixelCalc,centroidsCalc, colorIdx,INPUT_DIR,DIR_O, ), callback = collectResult)

		log(2, [ "Waiting for completion..." ])
		pool.close()
		pool.join()
		
		log(1, [ "Completed: " + str(processRes) ])
		if (sum(processRes) == 0):
			returnValue = 0		
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
		log(1, [ "Error: " + ''.join('!! ' + line for line in lines) ])  # Log it or whatever here

	return returnValue

def runComputation(imageDx,imageDy,imageDz, colors,coloridx,calculateout, V,FV, INPUT_DIR,BEST_IMAGE,BORDER_FILE,DIR_O):
	imageHeight,imageWidth = getImageData(INPUT_DIR+str(BEST_IMAGE)+PNG_EXTENSION)
	imageDepth = countFilesInADir(INPUT_DIR)
	Nx,Ny,Nz = imageHeight/imageDx, imageWidth/imageDx, imageDepth/imageDz
	returnValue = 2
	
	try:
		pixelCalc, centroidsCalc = centroidcalc(INPUT_DIR, BEST_IMAGE, colors)
		returnValue = startComputeChains(imageHeight,imageWidth,imageDepth, imageDx,imageDy,imageDz, Nx,Ny,Nz, calculateout,BORDER_FILE, colors,pixelCalc,centroidsCalc, coloridx,INPUT_DIR,DIR_O)
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
		log(1, [ "Error: " + ''.join('!! ' + line for line in lines) ])  # Log it or whatever here
		returnValue = 2
		
	sys.exit(returnValue)
	
def main(argv):
	ARGS_STRING = 'Args: -r -b <borderfile> -x <borderX> -y <borderY> -z <borderZ> -i <inputdirectory> -c <colors> -d <coloridx> -o <outputdir> -q <bestimage>'

	try:
		opts, args = getopt.getopt(argv,"rb:x:y:z:i:c:d:o:q:")
	except getopt.GetoptError:
		print ARGS_STRING
		sys.exit(2)
	
	nx = ny = nz = imageDx = imageDy = imageDz = 64
	colors = 2
	coloridx = 0
	
	mandatory = 6
	calculateout = False
	#Files
	BORDER_FILE = 'bordo3.json'
	BEST_IMAGE = ''
	DIR_IN = ''
	DIR_O = ''
	
	for opt, arg in opts:
		if opt == '-x':
			nx = ny = nz = imageDx = imageDy = imageDz = int(arg)
			mandatory = mandatory - 1
		elif opt == '-y':
			ny = nz = imageDy = imageDz = int(arg)
		elif opt == '-z':
			nz = imageDz = int(arg)
		elif opt == '-r':
			calculateout = True
		elif opt == '-i':
			DIR_IN = arg + '/'
			mandatory = mandatory - 1
		elif opt == '-b':
			BORDER_FILE = arg
			mandatory = mandatory - 1
		elif opt == '-o':
			mandatory = mandatory - 1
			DIR_O = arg
		elif opt == '-c':
			mandatory = mandatory - 1
			colors = int(arg)
		elif opt == '-d':
			mandatory = mandatory - 1
			coloridx = int(arg)			
		elif opt == '-q':
			BEST_IMAGE = int(arg)
			
	if mandatory != 0:
		print 'Not all arguments where given'
		print ARGS_STRING
		sys.exit(2)
		
	if (coloridx >= colors):
		print 'Not all arguments where given (coloridx >= colors)'
		print ARGS_STRING
		sys.exit(2)
		
	def ind(x,y,z): return x + (nx+1) * (y + (ny+1) * (z))
	
	chunksize = nx * ny + nx * nz + ny * nz + 3 * nx * ny * nz
	V = [[x,y,z] for z in xrange(nz+1) for y in xrange(ny+1) for x in xrange(nx+1) ]
	
	v2coords = invertIndex(nx,ny,nz)

	FV = []
	for h in xrange(len(V)):
		x,y,z = v2coords(h)
		if (x < nx) and (y < ny): FV.append([h,ind(x+1,y,z),ind(x,y+1,z),ind(x+1,y+1,z)])
		if (x < nx) and (z < nz): FV.append([h,ind(x+1,y,z),ind(x,y,z+1),ind(x+1,y,z+1)])
		if (y < ny) and (z < nz): FV.append([h,ind(x,y+1,z),ind(x,y,z+1),ind(x,y+1,z+1)])

	runComputation(imageDx, imageDy, imageDz, colors, coloridx, calculateout, V, FV, DIR_IN, BEST_IMAGE, BORDER_FILE, DIR_O)

if __name__ == "__main__":
	main(sys.argv[1:])