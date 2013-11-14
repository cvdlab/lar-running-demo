# Python
import numpy as np
from cython.parallel import prange
# Cython
cimport cython
cimport numpy as np
from cpython cimport bool
from cython.view cimport array as cvarray

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.nonecheck(False)
cdef int addr(int x, int y, int z, int nx, int ny, int nz) nogil: 
	return x + (nx) * (y + (ny) * (z))

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.nonecheck(False)
def setList(int nx, int ny, int nz, int colorIdx, np.ndarray[np.uint8_t, ndim=3] image, np.ndarray[np.int_t, ndim=1] saveTheColors):
	cdef list chains3D_old = range(0)
	
	for x in xrange(nx):
		for y in xrange(ny):
			for z in xrange(nz):
				if (image[z,x,y] == saveTheColors[colorIdx]):
					chains3D_old.append(addr(x,y,z,nx,ny,nz))
	
	return chains3D_old

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.nonecheck(False)
def setListNP(int nx, int ny, int nz, int colorIdx, np.ndarray[np.uint8_t, ndim=3] image, np.ndarray[np.int_t, ndim=1] saveTheColors):
	cdef bool hasSomeOne = False
	cdef np.ndarray[np.int32_t, ndim=1] chains3D = np.zeros(nx*ny*nz, dtype=np.int32)
	# cdef np.ndarray chains3D = np.zeros(nx*ny*nz,dtype=np.int_t);
	
	for x in xrange(nx):
		for y in xrange(ny):
			for z in xrange(nz):
				if (image[z,x,y] == saveTheColors[colorIdx]):
					hasSomeOne = True
					chains3D[addr(x,y,z,nx,ny,nz)] = 1
	
	return hasSomeOne,chains3D

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.nonecheck(False)
def setParallelListNP(int nx, int ny, int nz, int colorIdx, np.ndarray[np.uint8_t, ndim=3] image, np.ndarray[np.int_t, ndim=1] saveTheColors, int nThreads=4):
	cdef np.ndarray[np.int32_t, ndim=1] chains3D = np.zeros(nx*ny*nz, dtype=np.int32)
	cdef int [:] chains3D_view = chains3D
	
	cdef Py_ssize_t x,y,z
	cdef Py_ssize_t cx = nx
	cdef Py_ssize_t cy = ny
	cdef Py_ssize_t cz = nz
	cdef Py_ssize_t b = 0
	
	for x in prange(cx, nogil=True, schedule='guided', num_threads=nThreads):
		for y in prange(cy):
			for z in prange(cz):
				if (image[z,x,y] == saveTheColors[colorIdx]):
					b = 1
					chains3D_view[addr(x,y,z,nx,ny,nz)] = 1
	
	cdef bool hasSomeOne = False
	if (b == 1):
		hasSomeOne = True
		
	return hasSomeOne,chains3D

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.nonecheck(False)
def testList(int nx, int ny, int nz):
	cdef list chains3D_old = range(0)
	
	cdef list ry = range(ny)
	cdef list rz = range(nz)
	
	for x in xrange(nx):
		for y in ry:
			for z in rz:
				chains3D_old.append(addr(x,y,z,nx,ny,nz))
	
	return chains3D_old