from pyplasm import *
import getopt, sys
import traceback

# ------------------------------------------------------------
# Logging 
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

# ------------------------------------------------------------
            
def visualizeData(fileInput="output_big.obj"):
	batches=[]
	batches+=Batch.openObj(fileInput)
	octree=Octree(batches)
	glcanvas=GLCanvas()
	glcanvas.setOctree(octree)
	glcanvas.runLoop()

def main(argv):
	ARGS_STRING = 'Args: -i <inputfile>'

	try:
		opts, args = getopt.getopt(argv,"i:")
	except getopt.GetoptError:
		print ARGS_STRING
		sys.exit(2)
	
	mandatory = 1
	#Files
	FILE_IN = ''
	
	for opt, arg in opts:
		if opt == '-i':
			FILE_IN = arg
			mandatory = mandatory - 1
			
	if mandatory != 0:
		print 'Not all arguments where given'
		print ARGS_STRING
		sys.exit(2)
	
	try:
		visualizeData(FILE_IN)
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
		log(1, [ "Error: " + ''.join('!! ' + line for line in lines) ])
		sys.exit(2)
		
if __name__ == "__main__":
	main(sys.argv[1:])