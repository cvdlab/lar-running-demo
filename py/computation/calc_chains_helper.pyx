from cpython cimport bool
import numpy as np

cdef int addr(int x, int y, int z, int nx, int ny, int nz): return x + (nx) * (y + (ny) * (z))

def setList(int nx, int ny, int nz, int colorIdx, image,saveTheColors):
	chains3D_old = [];
	
	for x in range(nx):
		for y in range(ny):
			for z in range(nz):
				if (image[z,x,y] == saveTheColors[colorIdx]):
					chains3D_old.append(addr(x,y,z,nx,ny,nz))
	
	return chains3D_old
	
def setListNP(int nx, int ny, int nz, int colorIdx, image,saveTheColors):
	cdef bool hasSomeOne = False
	chains3D = np.zeros(nx*ny*nz,dtype=np.int32);
	
	for x in range(nx):
		for y in range(ny):
			for z in range(nz):
				if (image[z,x,y] == saveTheColors[colorIdx]):
					hasSomeOne = True
					chains3D[addr(x,y,z,nx,ny,nz)] = 1
	
	return hasSomeOne,chains3D
	
# def testNP(int nx, int ny, int nz, int colorIdx, image,saveTheColors):
#	cdef bool hasSomeOne = False
#	chains3D = np.zeros(nx*ny*nz,dtype=np.int32);
#	
#	return hasSomeOne,chains3D