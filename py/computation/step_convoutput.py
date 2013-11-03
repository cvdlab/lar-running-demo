from scipy import *
import json
import scipy
import numpy as np
import time as tm
import gc
import struct
import getopt, sys
import os

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

def writeOffsetToFile(file, offsetCurr):
	file.write( struct.pack('>I', offsetCurr[0]) )
	file.write( struct.pack('>I', offsetCurr[1]) )
	file.write( struct.pack('>I', offsetCurr[2]) )

def runComputation(FILE_IN,OUT_DIR):
	LISTA_VETTORI = []
	LISTA_OFFSET = []
	
	with open(FILE_IN, "r") as file:
		inputJson = json.load(file)
		LISTA_VETTORI = np.asarray(inputJson['lista_vettori'], dtype=np.dtype('b'))
		LISTA_OFFSET = np.asarray(inputJson['lista_offset'], dtype=np.int32)

	outputId = os.path.basename(FILE_IN).split('.')[0].split('-')[1]
	
	with open(OUT_DIR+'/output-'+outputId+'.bin', "wb") as file:
		i = 0
		while (i < len(LISTA_VETTORI)):
			writeOffsetToFile(file,LISTA_OFFSET[i])
			# print len(LISTA_VETTORI[i])
			file.write(bytearray(LISTA_VETTORI[i]))

			i = i + 1;
	
def main(argv):
	ARGS_STRING = 'Args: -i <inputfile> -o <outdir>'

	try:
		opts, args = getopt.getopt(argv,"i:o:")
	except getopt.GetoptError:
		print ARGS_STRING
		sys.exit(2)
	
	mandatory = 2
	#Files
	FILE_IN = ''
	OUT_DIR = ''
	
	for opt, arg in opts:
		if opt == '-i':
			FILE_IN = arg
			mandatory = mandatory - 1
		elif opt == '-o':
			OUT_DIR = arg
			mandatory = mandatory - 1
			
	if mandatory != 0:
		print 'Not all arguments where given'
		print ARGS_STRING
		sys.exit(2)
		
	try:
		runComputation(FILE_IN,OUT_DIR)
	except:
		print "Unexpected error:", sys.exc_info()[0]
		sys.exit(2)

if __name__ == "__main__":
   main(sys.argv[1:])