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
import ctypes

logging_level = 2; 

# 0 = no_logging
# 1 = few details
# 2 = many details
# 3 = many many details

def log(n, l):
	if __name__=="__main__" and n <= logging_level:
		for s in l:
			print "Log:", s;

result_list = []
def log_result(result):
    result_list.append(result)

def testProc(i):
	# time.sleep(0)
	return i[0]*2

def main(argv):
	processPool = max(1, multiprocessing.cpu_count()/2)
	print "Starting pool with: " + str(processPool)

	pool = multiprocessing.Pool(processPool)
	n = [1]

	print 'Start pool'
		
	for j in xrange(10):
		print "Added task: " + str(j) + "."

		pool.apply_async(testProc, args = (n,), callback = log_result)

	
	print "Waiting for completion..."
	pool.close()
	pool.join()
	print result_list

if __name__ == "__main__":
	main(sys.argv[1:])