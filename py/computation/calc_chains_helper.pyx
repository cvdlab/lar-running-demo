# Python
import numpy as np
from cython.parallel import prange
# Cython
cimport cython
cimport numpy as np
from cpython cimport bool

cdef int addr(int x, int y, int z, int nx, int ny, int nz): 
	return x + (nx) * (y + (ny) * (z))

def setList(int nx, int ny, int nz, int colorIdx, image,saveTheColors):
	chains3D_old = [];
	
	ry = range(ny)
	rz = range(nz)
	
	for x in xrange(nx):
		for y in ry:
			for z in rz:
				if (image[z,x,y] == saveTheColors[colorIdx]):
					chains3D_old.append(addr(x,y,z,nx,ny,nz))
	
	return chains3D_old
	
def setListNP(int nx, int ny, int nz, int colorIdx, image,saveTheColors):
	cdef bool hasSomeOne = False
	chains3D = np.zeros(nx*ny*nz,dtype=np.int32);
	
	ry = range(ny)
	rz = range(nz)
	
	for x in xrange(nx):
		for y in ry:
			for z in rz:
				if (image[z,x,y] == saveTheColors[colorIdx]):
					hasSomeOne = True
					chains3D[addr(x,y,z,nx,ny,nz)] = 1
	
	return hasSomeOne,chains3D
	
def setParallelListNP(int nx, int ny, int nz, int colorIdx, image,saveTheColors, nThreads=4):
	cdef bool hasSomeOne = False
	chains3D = np.zeros(nx*ny*nz,dtype=np.int32);
	
	cdef Py_ssize_t x
	cdef Py_ssize_t cx = nx
	
	for x in prange(cx, nogil=True, schedule='guided', num_threads=nThreads):
		with gil:
			for y in xrange(ny):
				for z in xrange(nz):
					if (image[z,x,y] == saveTheColors[colorIdx]):
						hasSomeOne = True
						chains3D[addr(x,y,z,nx,ny,nz)] = 1
	
	return hasSomeOne,chains3D