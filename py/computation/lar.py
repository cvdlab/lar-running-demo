# -*- coding: utf-8 -*-
"""
The MIT License
===============
    
Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import collections
import scipy.sparse
import numpy as np
from scipy import zeros,arange,mat,amin,amax
from scipy.sparse import vstack,hstack,csr_matrix,coo_matrix,lil_matrix,triu
from scipy.spatial import Delaunay
from scipy.linalg import *
from pyplasm import *
from matrixutil_no_accel import *
import time as tm


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

self_test=False

#------------------------------------------------------------------
#--geometry layer (using PyPlasm)----------------------------------
#------------------------------------------------------------------

def View (model):
    dims = range(1,1+RN(model))
    center = MED(dims)(model)
    model = T(dims)(SCALARVECTPROD([-1,center]))(model)
    VIEW(ROTN([-PI/3,[1,-1,0]])(R([1,2])(-PI/4)(model)))


def bezier(points):
    """
        To create a Bezier curve of degree n from a list of n+1 d-points.
        Each point is given as a list of coordinates.
        
        Return a geometric object of HPC (Hierarchical Polyhedral Complex) type.
    """
    return MAP(BEZIERCURVE(points))(INTERVALS(1)(20))

def CCOMB(vectors):
    """
        To create the convex combination of a list of vectors.
        Each vector is given as a list of coordinates.
        
        Return a vector.
    """
    return (COMP([ SCALARVECTPROD,CONS([ COMP([ DIV, CONS([K(1),LEN]) ]), VECTSUM ]) ]))(vectors)

def EXPLODE (sx,sy,sz):
    """
        To explode a HPC scene, given three real scaling parameters.
        sx,sy,sz >= 1.0
        
        Return a function to be applied to a list of HPC (Hierarchical Polyhedral Complex) objects.
    """
    def explode0 (scene):
        """
            To explode  a HPC scene, given as a list of HPC objects.
            Dimension-independent function (can be applied to points, edges, faces, cells, even mixed).
            Compute the centroid of each object, and apply to each of them a translation equal
            to the difference betwwen the scaled and the initial positions of its centroid.
            
            Return a single HPC object (the assembly of input objects, properly translated).
        """
        centers = [CCOMB(S1(UKPOL(obj))) for obj in scene]
        scalings = len(centers) * [S([1,2,3])([sx,sy,sz])]
        scaledCenters = [UK(APPLY(pair)) for pair in
                         zip(scalings, [MK(p) for p in centers])]
        translVectors = [ VECTDIFF((p,q)) for (p,q) in zip(scaledCenters, centers) ]
        translations = [ T([1,2,3])(v) for v in translVectors ]
        return STRUCT([ t(obj) for (t,obj) in zip(translations,scene) ])
    return explode0

def MKPOLS (model):
    """
        To MaKe a list of HPC objects from a LAR model.
        A LAR model is a pair, i.e. a Python tuple (V, FV), where
        -   V is the list of vertices, given as lists of coordinates;
        -   FV is the face-vertex relation, given as a list of faces,
            where each face is given as a list of vertex indices.
        
        Return a list of HPC objects.
    """
    V, FV = model
    pols = [MKPOL([[V[v] for v in f],[range(1,len(f)+1)], None]) for f in FV]
    return pols

def LAR2PLASM (topology):
    """
        To transform a topological relation from LAR format (base-index = 0, like C or python) 
        to PyPLASM format (base-index = 1, like fortran or matlab).
        topology stands for any LAR d_cell-vertex relation (es: EV, FV, CV, etc.)
        represented as a list of lists of integers (vertex indices in 0-basis).
        
        Return a list of lists of integers (vertex indices in 1-basis).
    """
    return AA(AA(lambda k: k+1))(topology)

def VERTS(geoms):
    """
        To generate the vertices of a grid of points from a list of d lists (of equal length) of numbers.
        geoms is the list of xcoods, ycoords, zcoords, etc., where xcoods, etc. is an increasing list of numbers.
        
        returns a properly ordered list of d-vertices, each given a list of numbers (vertex coordinates).
    """
    return COMP([AA(REVERSE),CART,REVERSE])(geoms)

def VERTEXTRUDE((V,coords)):
    """
        Utility function to generate the output model vertices in a multiple extrusion of a LAR model.
        V is a list of d-vertices (each given as a list of d coordinates).
        coords is a list of absolute translation parameters to be applied to V in order
        to generate the output vertices.
        
        Return a new list of (d+1)-vertices.
    """
    return CAT(AA(COMP([AA(AR),DISTR]))(DISTL([V,coords])))


def format(cmat,shape="csr"):
    """ Transform from list of triples (row,column,vale) 
        to scipy.sparse corresponding formats. 
        
        Return by default a csr format of a scipy sparse matrix.
    """
    n = len(cmat)
    data = arange(n)
    ij = arange(2*n).reshape(2,n)
    for k,item in enumerate(cmat):
        ij[0][k],ij[1][k],data[k] = item
    return scipy.sparse.coo_matrix((data, ij)).asformat(shape)


###################################################################

#------------------------------------------------------------------
#-- basic LAR software layer --------------------------------------
#------------------------------------------------------------------

#--coo is the standard rep using non-ordered triples of numbers----
#--coo := (row::integer, column::integer, value::float)------------


#------------------------------------------------------------------
def cooCreateFromBrc(ListOfListOfInt):
    COOm = [[k,col,1] for k,row in enumerate(ListOfListOfInt)
                   for col in row ]
    return COOm


#------------------------------------------------------------------
def csrCreateFromCoo(COOm):
    CSRm = format(COOm,"csr")
    return CSRm

#------------------------------------------------------------------
def csrCreate(BRCm,shape=(0,0)):
    if shape == (0,0):
        out = csrCreateFromCoo(cooCreateFromBrc(BRCm))
        return out
    else:
        CSRm = scipy.sparse.csr_matrix(shape)
        for i,j,v in cooCreateFromBrc(BRCm):
            CSRm[i,j] = v
        return CSRm

#------------------------------------------------------------------
def csrGetNumberOfRows(CSRm):
    Int = CSRm.shape[0]
    return Int

#------------------------------------------------------------------
def csrGetNumberOfColumns(CSRm):
    Int = CSRm.shape[1]
    return Int

#------------------------------------------------------------------
def csrToMatrixRepresentation(CSRm):
    nrows = csrGetNumberOfRows(CSRm)
    ncolumns = csrGetNumberOfColumns(CSRm)
    ScipyMat = zeros((nrows,ncolumns),int)
    C = CSRm.tocoo()
    for triple in zip(C.row,C.col,C.data):
        ScipyMat[triple[0],triple[1]] = triple[2]
    return ScipyMat

#------------------------------------------------------------------
def csrToBrc(CSRm):
    nrows = csrGetNumberOfRows(CSRm)
    C = CSRm.tocoo()
    out = [[] for i in xrange (nrows)]
    [out[i].append(j) for i,j in zip(C.row,C.col)]
    return out

#------------------------------------------------------------------
#--matrix utility layer--------------------------------------------
#------------------------------------------------------------------

#------------------------------------------------------------------
def csrIsA(CSRm):
    test = CSRm.check_format(True)
    return test==None

#------------------------------------------------------------------
def csrGet(CSRm,row,column):
    Num = CSRm[row,column]
    return Num

#------------------------------------------------------------------
def csrSet(CSRm,row,column,value):
    CSRm[row,column] = value
    return None

#------------------------------------------------------------------
def csrAppendByRow(CSRm1,CSRm2):
    CSRm = vstack([CSRm1,CSRm2])
    return CSRm

#------------------------------------------------------------------
def csrAppendByColumn(CSRm1,CSRm2):
    CSRm = hstack([CSRm1,CSRm2])
    return CSRm

#------------------------------------------------------------------
def csrSplitByRow(CSRm,k):
    CSRm1 = CSRm[:k]
    CSRm2 = CSRm[k:]
    return CSRm1,CSRm2

#------------------------------------------------------------------
def csrSplitByColumn(CSRm,k):
    CSRm1 = CSRm.T[:k]
    CSRm2 = CSRm.T[k:]
    return CSRm1.T,CSRm2.T

#------------------------------------------------------------------
#--sparse matrix operations layer----------------------------------
#------------------------------------------------------------------

def csrBoundaryFilter(CSRm, facetLengths):
	maxs = [max(CSRm[k].data) for k in xrange(CSRm.shape[0])]
	inputShape = CSRm.shape

	coo = CSRm.tocoo()

	row = [] # np.array([]).astype(np.int32);
	col = [] # np.array([]).astype(np.int32);
    # data = [] # np.array([]).astype(np.int32);

	k = 0
	while (k < len(coo.data)):      
		if coo.data[k] == maxs[coo.row[k]]:
			row.append(coo.row[k])
			col.append(coo.col[k])
		k += 1
    
	data = np.ones(len(col),dtype=np.int32);
	mtx = coo_matrix( (data, ( np.array(row).astype(np.int32), np.array(col).astype(np.int32) )), shape=inputShape)

	out = mtx.tocsr()
	return out

#------------------------------------------------------------------
def csrBinFilter(CSRm):
    # can be done in parallel (by rows)
	inputShape = CSRm.shape
	coo = CSRm.tocoo()
    
	k = 0
	while (k < len(coo.data)):
		if (coo.data[k] % 2 == 1): 
			coo.data[k] = 1
		else: 
			coo.data[k] = 0
		k += 1
    #mtx = coo_matrix((coo.data, (coo.row, coo.col)), shape=inputShape)
    #out = mtx.tocsr()
    #return out
	return coo.tocsr()

#------------------------------------------------------------------
def csrPredFilter(CSRm, pred):
    # can be done in parallel (by rows)
    coo = CSRm.tocoo()
    triples = [[row,col,val] for row,col,val in zip(coo.row,coo.col,coo.data)
               if pred(val)]
    i, j, data = TRANS(triples)
    CSRm = scipy.sparse.coo_matrix((data,(i,j)),CSRm.shape).tocsr()
    return CSRm

#------------------------------------------------------------------
#--topology interface layer----------------------------------------
#------------------------------------------------------------------

#------------------------------------------------------------------
def csrCreateTotalChain(kn):
    csrMat = csrCreateFromCoo(cooCreateFromBrc(TRANS([kn*[0]])))
    return csrMat

#------------------------------------------------------------------
def csrCreateUnitChain(kn,k):
    CSRout = lil_matrix((kn, 1))
    CSRout[k,0] = 1
    return CSRout.tocsr()

#------------------------------------------------------------------
def csrExtractAllGenerators(CSRm):
    listOfListOfNumerals = [csrTranspose(CSRm)[k].tocoo().col.tolist()
                            for k in xrange(CSRm.shape[1])]
    return listOfListOfNumerals

#------------------------------------------------------------------
def csrChainToCellList(CSRm):
    coo = CSRm.tocoo()
    ListOfInt = [theRow for k,theRow in enumerate(coo.row) if coo.data[k]==1]
    return ListOfInt

#------------------------------------------------------------------
#--topology query layer--------------------------------------------
#------------------------------------------------------------------

#------------------------------------------------------------------
def larCellAdjacencies(CSRm):
    CSRm = matrixProduct(CSRm,csrTranspose(CSRm))
    return CSRm

#------------------------------------------------------------------
def larCellIncidences(CSRm1,CSRm2):
    return matrixProduct(CSRm1, csrTranspose(CSRm2))

#------------------------------------------------------------------
# FV = d-chain;  EV = (d-1)-chain

def larBoundary(EV,FV):
    e = len(EV)
    f = len(FV)
    v = max(AA(max)(FV))+1
    #v = FV[-1][-1]+1  # at least with images ...
    csrFV = csrCreate(FV)#,shape=(f,v))
    csrEV = csrCreate(EV)#,shape=(e,v))
    facetLengths = [csrCell.getnnz() for csrCell in csrEV]
    temp = larCellIncidences(csrEV,csrFV)
    csrBoundary_2 = csrBoundaryFilter(temp,facetLengths)
    return csrBoundary_2

#------------------------------------------------------------------
def larBoundaryChain(csrBoundaryMat,brcCellList):
    n,m = csrBoundaryMat.shape
    data = scipy.ones(len(brcCellList))
    i = brcCellList
    j = scipy.zeros(len(brcCellList))
    csrChain = coo_matrix((data,(i,j)),shape=(m,1)).tocsr()
    csrmat = matrixProduct(csrBoundaryMat,csrChain)
    out = csrBinFilter(csrmat)
    return out

#------------------------------------------------------------------
def larCoboundaryChain(csrCoBoundaryMat,brcCellList):
    m = csrGetNumberOfColumns(csrCoBoundaryMat)
    csrChain = sum([csrCreateUnitChain(m,k) for k in brcCellList])
    return csrBinFilter(matrixProduct(csrCoBoundaryMat,csrChain))

#------------------------------------------------------------------
#--model geometry layer--------------------------------------------
#--larOp : model -> model------------------------------------------
#------------------------------------------------------------------
# model = (vertices, topology)
#------------------------------------------------------------------
# binary product of cell complexes

def larProduct(models):
    model1,model2 = models
    V, cells1 = model1
    W, cells2 = model2
    verts = collections.OrderedDict(); k = 0
    for v in V:
        for w in W:
            vertex = tuple(v+w)
            if not verts.has_key(vertex):
                verts[vertex] = k
                k += 1
    cells = [ sorted([verts[tuple(V[v]+W[w])] for v in c1 for w in c2])
             for c1 in cells1 for c2 in cells2]

    model = AA(list)(verts.keys()), sorted(cells)
    return model

#------------------------------------------------------------------
# extrusion of simplicial complexes
# combinatorial algorithm

def cumsum(iterable):
    # cumulative addition: list(cumsum(range(4))) => [0, 1, 3, 6]
    iterable = iter(iterable)
    s = iterable.next()
    yield s
    for c in iterable:
        s = s + c
        yield s

def larExtrude(model,pattern):
    V,FV = model
    d = len(FV[0])
    offset = len(V)
    m = len(pattern)
    outcells = []
    for cell in FV:
        # create the indices of vertices in the cell "tube"
        tube = [v + k*offset for k in xrange(m+1) for v in cell]
        # take groups of d+1 elements, via shifting by one
        rangelimit = len(tube)-d
        cellTube = [tube[k:k+d+1] for k in xrange(rangelimit)]
        outcells += [scipy.reshape(cellTube,newshape=(m,d,d+1)).tolist()]
    outcells = AA(CAT)(TRANS(outcells))
    outcells = [group for k,group in enumerate(outcells) if pattern[k]>0 ]
    coords = list(cumsum([0]+(AA(ABS)(pattern))))
    outVerts = VERTEXTRUDE((V,coords))
    newModel = outVerts, CAT(outcells)
    return newModel

def EXTRUDE(args):
    model = ([[]],[[0]])
    for k,steps in enumerate(args):
        model = larExtrude(model,steps*[1])
    V,cells = model
    verts = AA(list)(scipy.array(V) / AA(float)(args))
    return [verts, AA(AA(lambda h:h+1))(cells)]

#------------------------------------------------------------------
# extraction of facets of a cell complex

def setup(model,dim):
    V, cells = model
    csr = csrCreate(cells)
    csrAdjSquareMat = larCellAdjacencies(csr)
    csrAdjSquareMat = csrPredFilter(csrAdjSquareMat, GE(dim)) # ? HOWTODO ?
    return V,cells,csr,csrAdjSquareMat

def larFacets(model,dim=3):
    """
        Estraction of (d-1)-cellFacets from model := (V,d-cells)
        Return (V, (d-1)-cellFacets)
    """
    V,cells,csr,csrAdjSquareMat = setup(model,dim)
    cellFacets = []
    # for each input cell i
    for i in xrange(len(cells)):
        adjCells = csrAdjSquareMat[i].tocoo()
        cell1 = csr[i].tocoo().col
        pairs = zip(adjCells.col,adjCells.data)
        for j,v in pairs:
            if (i<j):
                cell2 = csr[j].tocoo().col
                cell = list(set(cell1).intersection(cell2))
                cellFacets.append(sorted(cell))
    # sort and remove duplicates
    cellFacets = sorted(AA(list)(set(AA(tuple)(cellFacets))))
    return V,cellFacets

#------------------------------------------------------------------
# extraction of skeletons of a (grid) cell complex


def larSkeletons (model,dim=3):
    """
        Estraction of all skeletons from model := (V,d-cells)
        Return (V, [d-cells, (d-1)-cells, ..., 1-cells]) where p-cells is a list_of_lists_of_integers
        """
    faces = []
    faces.append(model[1])
    for p in xrange(dim,0,-1):
        model = larFacets(model,dim=p)
        faces.append(model[1])
    return model[0], REVERSE(faces)


def boundarGrid(model,minPoint,maxPoint):
    """
        Build the set of the outerCells of a cuboidal model.
        Return a list of (degenerate) d-cells
        """
    dim = len(minPoint)
    # boundary points extraction
    outerCells = [[] for k in xrange(2*dim)]
    for n,point in enumerate(model[0]):
        for h,coord in enumerate(point):
            if coord == minPoint[h]: outerCells[h].append(n)
            if coord == maxPoint[h]: outerCells[dim+h].append(n)
    return outerCells


def outerVertexTest (bounds):
    """
        Look whether v is on the boundary of a unconnected (multi-dim) interval [vmin_0,vmax_0, ... ,vmin_n,vmax_n]
        Return a Boolean value
        """
    def test0 (v):
        return OR(AA(EQ)(CAT(AA(TRANS)(DISTR([bounds,v])))))
    return test0