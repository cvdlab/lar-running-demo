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
#
import matplotlib.pyplot as plt

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

PNG_EXTENSION = ".png"

# ------------------------------------------------------------
# Utility toolbox
# ------------------------------------------------------------

def countFilesInADir(directory):
	return len(os.walk(directory).next()[2])
	
# ------------------------------------------------------------

def computeChains(imageHeight,imageWidth,imageDepth, imageDx,imageDy,imageDz, Nx,Ny,Nz, calculateout,bordo3, colors,pixelCalc,centroidsCalc, INPUT_DIR,DIR_O):
	beginImageStack = 0
	endImage = beginImageStack
	MAX_CHAINS = colors
	count = 0
	
	LISTA_VETTORI = {}
	LISTA_VETTORI2 = {}
	LISTA_OFFSET = {}
	
	# print str(imageHeight) + '-' + str(imageWidth) + '-' + str(imageDepth)
	# print str(imageDx) + '-' + str(imageDy) + '-' + str(imageDz)
	# print str(Nx) + '-' + str(Ny) + '-' + str(Nz)
	
	for zBlock in range(imageDepth/imageDz):
		startImage = endImage
		endImage = startImage + imageDz
		xEnd, yEnd = 0,0
		theImage,colors,theColors = pngstack2array3d(INPUT_DIR, startImage, endImage, colors, pixelCalc, centroidsCalc)
	
		theColors = theColors.reshape(1,2) # colors??
		
		# print 'Z now:' + str(zBlock)
		
		background = max(theColors[0])
		foreground = min(theColors[0])
		
		for xBlock in range(imageHeight/imageDx):
			
			for yBlock in range(imageWidth/imageDy):
				
				xStart, yStart = xBlock * imageDx, yBlock * imageDy
				xEnd, yEnd = xStart+imageDx, yStart+imageDy
				
				# print str(xStart) + '-' + str(xEnd)
				# print str(yStart) + '-' + str(yEnd)
				
				image = theImage[:, xStart:xEnd, yStart:yEnd]
				nz,nx,ny = image.shape
				# print str(nx) + '-' + str(ny) + '-' + str(nz)
				# print str(len(image[0])) + '-' + str(len(image[nz-1]))
				# plt.imshow(image[0])
				# plt.show()
				# plt.imshow(image[nz-1])
				# plt.show()
				
				count += 1

				# Compute a quotient complex of chains with constant field
				# ------------------------------------------------------------

				chains3D_old = {};
				chains3D = {};
				
				for currCol in theColors[0]:
					chains3D_old.update({str(currCol): []})
					chains3D.update({str(currCol): np.zeros(nx*ny*nz,dtype=int32)})

				zStart = startImage - beginImageStack;

				def addr(x,y,z): return x + (nx) * (y + (ny) * (z))
				
				if (calculateout == True):
					for x in range(nx):
						for y in range(ny):
							for z in range(nz):
								for currCol in theColors[0]:
									if (image[z,x,y] == currCol):
										# tmpChain = chains3D[str(currCol)]
										# tmpChain[addr(x,y,z)] = 1
										# chains3D.update({str(currCol): tmpChain})
										##
										tmpChain = chains3D_old[str(currCol)]
										tmpChain.append(addr(x,y,z))
										chains3D_old.update({str(currCol): tmpChain})
				else:
					for x in range(nx):
						for y in range(ny):
							for z in range(nz):
								for currCol in theColors[0]:
									# print str(x) + '-' + str(y) + '-' + str(z) + '-' + str(currCol)
									if (image[z,x,y] == currCol):
										tmpChain = chains3D[str(currCol)]
										tmpChain[addr(x,y,z)] = 1
										chains3D.update({str(currCol): tmpChain})

				# Compute the boundary complex of the quotient cell
				# ------------------------------------------------------------

				# timer_last = tm.time();
				objectBoundaryChain = {}
				if (calculateout == True):
					for currCol in theColors[0]:
						objectBoundaryChain.update( {str(currCol): larBoundaryChain(bordo3,chains3D_old[str(currCol)])} )
				
				# temp = objectBoundaryChain.toarray().astype(int32).flatten()
				# l = len(temp)
				# objectBoundaryChain_correct = scipy.sparse.csr_matrix((temp.reshape((l,1))))
				# tempo_larboundary = tempo_larboundary + tm.time() - timer_last;
				# print "Tempo larBoundaryChain() =", tempo_larboundary
				# print 'Update results for: ' + str(xBlock) + '-' + str(yBlock)
				for currCol in theColors[0]:
					if ((xBlock == 0) and (yBlock == 0) and (zBlock == 0)):
						LISTA_OFFSET.update( {str(currCol): np.array([[zStart,xStart,yStart]], dtype=int32)} )
						if (calculateout == True):
							LISTA_VETTORI2.update( {str(currCol): np.array([objectBoundaryChain[str(currCol)].toarray().astype(int32).flatten()])} )
						else:
							LISTA_VETTORI.update( {str(currCol): np.array([chains3D[str(currCol)]], dtype=int32)} )
					else:
						LISTA_OFFSET.update( {str(currCol): np.append(LISTA_OFFSET[str(currCol)], np.array([[zStart,xStart,yStart]], dtype=int32), axis=0)} )
						if (calculateout == True):
							LISTA_VETTORI2.update( {str(currCol): np.append(LISTA_VETTORI2[str(currCol)], [objectBoundaryChain[str(currCol)].toarray().astype(int32).flatten()], axis=0)} )
						else:
							LISTA_VETTORI.update( {str(currCol): np.append(LISTA_VETTORI[str(currCol)], [chains3D[str(currCol)]], axis=0)} )
							
	for key in LISTA_OFFSET:
		if (calculateout == True):
			with open(DIR_O+'/output-'+key+'.json', "w") as file:
				json.dump({"lista_vettori":LISTA_VETTORI2[key].tolist(), "lista_offset":LISTA_OFFSET[key].tolist()}, file, separators=(',',':'))
				file.flush()
		else:
			with open(DIR_O+'/selettori-'+key+'.json', "w") as file:
				json.dump({"lista_vettori":LISTA_VETTORI[key].tolist(), "lista_offset":LISTA_OFFSET[key].tolist()}, file, separators=(',',':'))
				file.flush()

def runComputation(imageDx,imageDy,imageDz, colors,calculateout, V,FV, INPUT_DIR,BEST_IMAGE,BORDER_FILE,DIR_O):
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

	imageHeight,imageWidth = getImageData(INPUT_DIR+str(BEST_IMAGE)+".png")
	imageDepth = countFilesInADir(INPUT_DIR)
	
	Nx,Ny,Nz = imageHeight/imageDx, imageWidth/imageDx, imageDepth/imageDz
	try:
		pixelCalc, centroidsCalc = centroidcalc(INPUT_DIR, BEST_IMAGE, colors)
		computeChains(imageHeight,imageWidth,imageDepth, imageDx,imageDy,imageDz, Nx,Ny,Nz, calculateout,bordo3, colors,pixelCalc,centroidsCalc, INPUT_DIR,DIR_O)
	except:
		print "Unexpected error:", sys.exc_info()[0]
		sys.exit(2)
	
def main(argv):
	ARGS_STRING = 'Args: -r -b <borderfile> -x <borderX> -y <borderY> -z <borderZ> -i <inputdirectory> -c <colors> -o <outputdir> -q <bestimage>'

	try:
		opts, args = getopt.getopt(argv,"rb:x:y:z:i:c:o:q:")
	except getopt.GetoptError:
		print ARGS_STRING
		sys.exit(2)
	
	nx = ny = nz = imageDx = imageDy = imageDz = 64
	colors = 2
	
	mandatory = 5
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
		elif opt == '-q':
			BEST_IMAGE = int(arg)
			
	if mandatory != 0:
		print 'Not all arguments where given'
		print ARGS_STRING
		sys.exit(2)
		
	def ind(x,y,z): return x + (nx+1) * (y + (ny+1) * (z))

	def invertIndex(nx,ny,nz):
		nx,ny,nz = nx+1,ny+1,nz+1
		def invertIndex0(offset):
			a0, b0 = offset / nx, offset % nx
			a1, b1 = a0 / ny, a0 % ny
			a2, b2 = a1 / nz, a1 % nz
			return b0,b1,b2
		return invertIndex0
	
	chunksize = nx * ny + nx * nz + ny * nz + 3 * nx * ny * nz
	V = [[x,y,z] for z in range(nz+1) for y in range(ny+1) for x in range(nx+1) ]
	
	v2coords = invertIndex(nx,ny,nz)

	FV = []
	for h in range(len(V)):
		x,y,z = v2coords(h)
		if (x < nx) and (y < ny): FV.append([h,ind(x+1,y,z),ind(x,y+1,z),ind(x+1,y+1,z)])
		if (x < nx) and (z < nz): FV.append([h,ind(x+1,y,z),ind(x,y,z+1),ind(x+1,y,z+1)])
		if (y < ny) and (z < nz): FV.append([h,ind(x,y+1,z),ind(x,y,z+1),ind(x,y+1,z+1)])

	runComputation(imageDx, imageDy, imageDz, colors, calculateout, V, FV, DIR_IN, BEST_IMAGE, BORDER_FILE, DIR_O)

if __name__ == "__main__":
   main(sys.argv[1:])