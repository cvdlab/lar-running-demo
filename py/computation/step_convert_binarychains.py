from scipy import *
import json
import scipy
import numpy as np
import time as tm
import gc
import struct
import getopt, sys
import os
import traceback

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

# ------------------------------------------------------------

# inputFile = output.bin
# outputVtx = outputVtx.obj
# outputFaces = outputFaces.obj

def readFile(V,FV,chunksize,inputFile,OUT_DIR): #outputVtx="outputVtx.obj",outputFaces="outputFaces.obj"):
	outputId = os.path.basename(inputFile).split('.')[0].split('-')[1]
	outputFile=OUT_DIR+"/selettori-"+outputId+".json"
	LISTA_VETTORI = None
	LISTA_OFFSET = None
	createdLV = False
	
	with open(inputFile, "rb") as file:
		try:
			while True:
				count += 1

				zStart = struct.unpack('>I', file.read(4))[0]
				xStart = struct.unpack('>I', file.read(4))[0]
				yStart = struct.unpack('>I', file.read(4))[0]
					
				log(1, ["zStart, xStart, yStart = " + str(zStart) + "," + str(xStart) + "," + str(yStart)]);
				#	zStart, xStart, yStart = LISTA_OFFSET[i].astype(float64)

				currentChain = np.zeros(chunksize,dtype=int32);

				# log(1, ["chunksize = " + str(chunksize)]);
				temp = file.read(chunksize);
				# log(1, ["chunksize = OK"]);

				i = 0
				timer_start("currentChain " + str(i));
				while (i < chunksize):
					if (temp[i] == '\x01'):
						currentChain[i] = 1;
					i = i + 1;
				timer_stop();
				log(1, ["currentChain[i] = " + str(i)]);
					
				if (createdLV == False):
					LISTA_OFFSET = np.array([[zStart,xStart,yStart]], dtype=int32)
					LISTA_VETTORI = np.array([currentChain], dtype=int32)
					createdLV = True
				else:
					LISTA_OFFSET = np.append(LISTA_OFFSET, np.array([[zStart,xStart,yStart]], dtype=int32), axis=0)
					LISTA_VETTORI = np.append(LISTA_VETTORI, [currentChain], axis=0)
		except:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
			log(1, [ "EOF or error: " + ''.join('!! ' + line for line in lines) ])
			
	with open(outputFile, "w") as file:
		json.dump({"lista_vettori":LISTA_VETTORI.tolist(), "lista_offset":LISTA_OFFSET.tolist()}, file, separators=(',',':'))
		file.flush()
		
def main(argv):
	ARGS_STRING = 'Args: -x <borderX> -y <borderY> -z <borderZ> -i <inputfile> -o <outdir>'
	
	try:
		opts, args = getopt.getopt(argv,"i:o:x:y:z:")
	except getopt.GetoptError:
		print ARGS_STRING
		sys.exit(2)
	
	nx = ny = nz = 64
	mandatory = 3
	#Files
	FILE_IN = ''
	OUT_DIR = ''
	
	for opt, arg in opts:
		if opt == '-x':
			nx = ny = nz = int(arg)
			mandatory = mandatory - 1
		elif opt == '-y':
			ny = nz = int(arg)
		elif opt == '-z':
			nz = int(arg)
		elif opt == '-i':
			FILE_IN = arg
			mandatory = mandatory - 1
		elif opt == '-o':
			OUT_DIR = arg
			mandatory = mandatory - 1
			
	if mandatory != 0:
		print 'Not all arguments where given'
		print ARGS_STRING
		sys.exit(2)
	
	chunksize = nx * ny * nz

	try:
		readFile(chunksize,FILE_IN,OUT_DIR)
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
		log(1, [ "Error: " + ''.join('!! ' + line for line in lines) ])
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])