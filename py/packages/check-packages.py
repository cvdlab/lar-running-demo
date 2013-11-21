import sys

packages = []
packages.extend(['collections', 'scipy', 'numpy', 'pyplasm', 'time']) # LAR
packages.extend(['sys', 'logging', 'simplejson', 'json', 'requests', 'termcolor']) # mtx-accel
packages.extend(['png', 'matplotlib', 'struct']) # pngstack
packages.extend(['pyximport']) # cython
packages.extend(['multiprocessing', 'Queue']) # multiprocessing
packages.extend(['time', 'gc', 'os', 'traceback']) # generic

def main(argv):
	fullpkg = True

	for pkg in packages:
		try:
			__import__(pkg)
		except ImportError:
			fullpkg = False
			print "Missing package: " + pkg
	
	if fullpkg == False:
		sys.exit(2)
	
	sys.exit(0)

if __name__ == "__main__":
   main(sys.argv[1:])
