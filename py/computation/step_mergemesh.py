import time as tm
import gc
import getopt, sys
import os
import traceback
import glob

# ------------------------------------------------------------
# Logging & Timer 
# ------------------------------------------------------------

logging_level = 1; 

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

def mergeFiles(listFile, outDir):
	with file(outDir+'/mergedMesh-Vtx.lst', 'w') as outVtxFile:
		with file(outDir+'/mergedMesh-Faces.lst', 'w') as outFacesFile:
			vertexEnum = 0
			firstFile = True
		
			for currentMesh in listFile:
				with file(currentMesh) as currFile:
					currOffset = vertexEnum
					for currLine in currFile:
						if currLine.startswith("v"):
							vertexEnum = vertexEnum + 1
							outVtxFile.write(currLine)
						elif currLine.startswith("f"):
							if (firstFile == True):
								outFacesFile.write(currLine)
							else:
								triFace = currLine.split()
								outFacesFile.write(triFace[0] + ' ' + str(int(triFace[1])+currOffset) + ' ' + str(int(triFace[2])+currOffset) + ' ' + str(int(triFace[3])+currOffset)+ '\n')
				# first file done
				firstFile = False
				log(1, [ "VtxCount: " + str(vertexEnum) ])
	
	with file(outDir+'/mergedMesh.obj', 'w') as finalMesh:
		with file(outDir+'/mergedMesh-Vtx.lst', 'r') as outVtxFile:
			finalMesh.write(outVtxFile.read())
		with file(outDir+'/mergedMesh-Faces.lst', 'r') as outFacesFile:
			finalMesh.write(outFacesFile.read())
	
	os.remove(outDir+'/mergedMesh-Vtx.lst')
	os.remove(outDir+'/mergedMesh-Faces.lst')
	
def main(argv):
	ARGS_STRING = 'Args: -i <inputdir> -o <outdir>'
	
	try:
		opts, args = getopt.getopt(argv,"i:o:")
	except getopt.GetoptError:
		print ARGS_STRING
		sys.exit(2)
	
	mandatory = 2
	#Files
	IN_DIR = ''
	OUT_DIR = ''
	
	for opt, arg in opts:
		if opt == '-i':
			IN_DIR = arg
			mandatory = mandatory - 1
		elif opt == '-o':
			OUT_DIR = arg
			mandatory = mandatory - 1
			
	if mandatory != 0:
		print 'Not all arguments where given'
		print ARGS_STRING
		sys.exit(2)

	
	try:
		listFile = glob.glob(IN_DIR+'/*.obj')
		mergeFiles(listFile,OUT_DIR)
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
		log(1, [ "Error: " + ''.join('!! ' + line for line in lines) ])
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])