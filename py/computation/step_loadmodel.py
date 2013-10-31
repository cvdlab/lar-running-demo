from pyplasm import *
import getopt, sys

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
		
	visualizeData(FILE_IN)
			
if __name__ == "__main__":
   main(sys.argv[1:])