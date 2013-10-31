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
from time import time


timer = 1;

timer_last =  time()

def timer_start(s):

    global timer_last;
    if __name__=="__main__" and timer == 1:   
        print "Timer start:", s;
    timer_last = time();

def timer_stop():

    global timer_last;
    if __name__=="__main__" and timer == 1:   
        print "Timer stop :", time() - timer_last;
#
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
    out = [[] for i in range (nrows)]
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
    
    maxs = [max(CSRm[k].data) for k in range(CSRm.shape[0])]
    inputShape = CSRm.shape
    
    coo = CSRm.tocoo()

    row = [] # np.array([]).astype(np.int32);
    col = [] # np.array([]).astype(np.int32);
    data = [] # np.array([]).astype(np.int32);

    for k in range(len(coo.data)):      
        if coo.data[k] == maxs[coo.row[k]]:
            row.append(coo.row[k])
            col.append(coo.col[k])
            data.append(1)
    
    mtx = coo_matrix( (np.array(data).astype(np.int32), ( np.array(row).astype(np.int32), np.array(col).astype(np.int32) )), shape=inputShape)

    out = mtx.tocsr()
    return out

#------------------------------------------------------------------
def csrBinFilter(CSRm):
    # can be done in parallel (by rows)
    inputShape = CSRm.shape
    coo = CSRm.tocoo()
    for k in range(len(coo.data)):
        if coo.data[k] % 2 == 1: coo.data[k] = 1
        else: coo.data[k] = 0
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
                            for k in range(CSRm.shape[1])]
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
        tube = [v + k*offset for k in range(m+1) for v in cell]
        # take groups of d+1 elements, via shifting by one
        rangelimit = len(tube)-d
        cellTube = [tube[k:k+d+1] for k in range(rangelimit)]
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
    for i in range(len(cells)):
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
    for p in range(dim,0,-1):
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
    outerCells = [[] for k in range(2*dim)]
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



#------------------------------------------------------------------
#--imaging layer (enumerative schemes w integer coords)------------
#------------------------------------------------------------------

#-------------------------------------------------------------------
# 2D image toolbox
'''
def crossGrow(image,cross):
    xm,x,xM,ym,y,yM = cross
    pointValue = image[x,y]
    if xm > 0 and image[xm-1,y] == pointValue: xm -= 1
    if xM < 49 and image[xM+1,y] == pointValue: xM += 1
    if ym > 0 and image[x,ym-1] == pointValue: ym -= 1
    if yM < 49 and image[x,yM+1] == pointValue: yM += 1
    return xm,x,xM,ym,y,yM

def xbar(image,span,xspan):
    xm,x0,xM,y0 = span
    xmin,xMAX = xspan
    pointValue = image[x0,y0]
    if xm > xmin and image[xm-1,y0] == pointValue: xm -= 1
    if xM < xMAX and image[xM+1,y0] == pointValue: xM += 1
    return xm,x0,xM,y0

def ybar(image,span,yspan):
    x0,ym,y0,yM = span
    ymin,yMAX = yspan
    pointValue = image[x0,y0]
    if ym > ymin and image[x0,ym-1] == pointValue: ym -= 1
    if yM < yMAX and image[x0,yM+1] == pointValue: yM += 1
    return x0,ym,y0,yM

def delta(p,q): # area of rectangle (q,p)
    vect = AA(abs)(VECTDIFF([p,q]))
    return vect[0] * vect[1]
'''
#-------------------------------------------------------------------
# 2D images to lar model
'''
def write2DBlock(cooStore):
    def write2DBlock0(block):
        x0,y0,dx,dy = block
        [(cooStore.append([x0,j,1]), cooStore.append([x0+dx,j,1])) for j in range(y0,y0+dy+1)]
        [(cooStore.append([i,y0,1]), cooStore.append([i,y0+dy,1])) for i in range(x0,x0+dx+1)]
        return cooStore
    return write2DBlock0


def read2DBlock(lilStore):
    def read2DBlock0(block):
        x,y,dx,dy = block
        outBlock = [[(i,y) for i in range(x,x+dx) if lilStore[i,y] > 2]]
        outBlock.append([(x+dx,j) for j in range(y,y+dy) if lilStore[x+dx,j] > 2])
        outBlock.append([(i,y+dy) for i in range(x+dx,x,-1) if lilStore[i,y+dy] > 2])
        outBlock.append([(x,j) for j in range(y+dy,y,-1) if lilStore[x,j] > 2])
        return CAT(outBlock)
    return read2DBlock0


def lar2DFromImageBlocks(blocks):
    
    # translation that moves the (xmin,ymin) point to the origin
    xmin,ymin = AA(min)(TRANS([block[0:2] for block in blocks]))
    blocks = [[x-xmin,y-ymin,dx,dy] for [x,y,dx,dy] in blocks]
    
    # store initialization
    cooStore = []
    def computeShape(blocks):
        return AA(max)(TRANS([[x+dx,y+dy] for [x,y,dx,dy] in blocks]))
    ax,ay = computeShape(blocks)
    cooStore.append([0,0,2])
    cooStore.append([ax,0,2])
    cooStore.append([0,ay,2])
    cooStore.append([ax,ay,2])

    # forward step (writing the boundary of each block)
    for block in blocks:
        write2DBlock(cooStore)(block)
    lilStore = csrCreateFromCoo(cooStore).tolil()

    # backward step (reading the boundary of each block)
    updatedBlock = [read2DBlock(lilStore)(block) for block in blocks]
    verts = collections.OrderedDict(); k = 0
    for block in updatedBlock:
        for vert in block:
            if vert not in verts:
                verts[vert] = k
                k += 1

    # encoding the output
    V = AA(AA(float))(verts.keys())
    F2V = [[verts[vert] for vert in block] for block in updatedBlock]

    # automatically adding the 4 exterior blocks of the 2D image
    xmin,ymin = AA(amin)(TRANS(V))
    xmax,ymax = AA(amax)(TRANS(V))
    exterior_xmin, exterior_xmax, exterior_ymin, exterior_ymax = [],[],[],[]
    for (key,value) in verts.items():
        if key[0] == xmin: exterior_xmin.append(value)
        if key[0] == xmax: exterior_xmax.append(value)
        if key[1] == ymin: exterior_ymin.append(value)
        if key[1] == ymax: exterior_ymax.append(value)

    model = V,F2V + [exterior_xmin, exterior_xmax, exterior_ymin, exterior_ymax]
    return model


if __name__=="__main__":
    blocks2D = [ [[0,0],[5,10]], [[5,0],[9,3]], [[9,0],[13,3]], [[5,3],[8,10]],  [[8,3],[13,10]], [[0,10],[9,12]]
                , [[9,10],[13,12]] ]
    
    blocks = [ CAT([ block[0],VECTDIFF(REVERSE(block)) ])  for block in blocks2D ]
    model = lar2DFromImageBlocks(blocks)
    V,faces = larSkeletons(model,dim=2)
    F0V, F1V, F2V = faces
    VIEW(EXPLODE(1.2,1.2,1.2)( MKPOLS((V,F2V[:-4])) ))
    VIEW(EXPLODE(1.2,1.2,1.2)( MKPOLS((V,F1V)) ))
    VIEW(EXPLODE(1.2,1.2,1.2)( MKPOLS((V,F0V+F1V+F2V[:-4])) ))

    boundary_2 = larBoundary(F1V,F2V[:-4])
    chain_1 = larBoundaryChain(boundary_2,range(len(F2V[:-4])))
    boundary_edges = csrChainToCellList(chain_1)
    edges = [F1V[e] for e in boundary_edges]
    VIEW(EXPLODE(1.2,1.2,1.2)( MKPOLS((V,edges)) ))


[
 [0,0,0],
 [5,0,0],
 [9,0,0],
 [13,0,0],
 [5,3,0],
 [8,3,0],
 [9,3,0],
 [13,3,0],
 [0,10,0],
 [5,10,0],
 [8,10,0],
 [9,10,0],
 [13,10,0],
 [0,12,0],
 [9,12,0],
 [13,12,0]]
'''
#-------------------------------------------------------------------
# 3D images to lar model

# TODO:
# Rewrite this section by using a stack of 2D sparse matrices
# the trick to use:  store[x,y,z] => store[z][x,y] ... :o)
# such a translation may be even encapsulated in a wrapping interface

'''
def write3DBlock(store):
    def write3DBlock0(block):
        x,y,z,dx,dy,dz = block
        for j in range(y,y+dy+1):
            for k in range(z,z+dz+1):
                store[x,j,k] += 1
                store[x+dx,j,k] += 1
        for k in range(z,z+dz+1):
            for i in range(x,x+dx+1):
                store[i,y,k] += 1
                store[i,y+dy,k] += 1
        for i in range(x,x+dx+1):
            for j in range(y,y+dy+1):
                store[i,j,z] += 1
                store[i,j,z+dz] += 1
        return store
    return write3DBlock0


def read3DBlock(store):
    def read3DBlock0(block):
        x,y,z,dx,dy,dz = block
        outBlock = [[(x,j,k) for j in range(y,y+dy+1) for k in range(z,z+dz+1) if store[x,j,k] > 3]]
        outBlock.append([(x+dx,j,k) for j in range(y,y+dy+1) for k in range(z,z+dz+1) if store[x+dx,j,k] > 3])
        outBlock.append([(i,y,k) for k in range(z,z+dz+1) for i in range(x,x+dx+1) if store[i,y,k] > 3])
        outBlock.append([(i,y+dy,k) for k in range(z,z+dz+1) for i in range(x,x+dx+1) if store[i,y+dy,k] > 3])
        outBlock.append([(i,j,z) for i in range(x,x+dx+1) for j in range(y,y+dy+1) if store[i,j,z] > 3])
        outBlock.append([(i,j,z+dz) for i in range(x,x+dx+1) for j in range(y,y+dy+1) if store[i,j,z+dz] > 3])
        return CAT(outBlock)
    return read3DBlock0


def lar3DFromImageBlocks(blocks):
    
    # translation that moves the (xmin,ymin,zmin) point to the origin
    xmin,ymin,zmin = AA(min)(TRANS([block[0:3] for block in blocks]))
    blocks = [[x-xmin,y-ymin,z-zmin,dx,dy,dz] for [x,y,z,dx,dy,dz] in blocks]
    
    # store initialization
    def computeShape(blocks):
        return AA(max)(TRANS([[x+dx,y+dy,z+dz] for [x,y,z,dx,dy,dz] in blocks]))
    ax,ay,az = computeShape(blocks)
    store = zeros(shape=(ax+1,ay+1,az+1),dtype=int)
    store[0,0,0] += 2
    store[ax,0,0] += 2
    store[0,ay,0] += 2
    store[0,0,az] += 2
    store[ax,ay,0] += 2
    store[ax,0,az] += 2
    store[0,ay,az] += 2
    store[ax,ay,az] += 2
    
    # forward step (writing the boundary of each block)
    [ write3DBlock(store)(block) for block in blocks ]
    store[ax,ay,az] += 2 # to solve the bug of the extreme vertex of the extreme block

    # backward step (reading the boundary of each block)
    updatedBlocks = [ read3DBlock(store)(block) for block in blocks ]
    verts = collections.OrderedDict(); k = 0
    for block in updatedBlocks:
        for vert in block:
            if vert not in verts:
                verts[vert] = k
                k += 1

    # encoding the output
    V = AA(AA(float))(verts.keys())
    F3V = [[verts[vert] for vert in block] for block in updatedBlocks]
                    
    # automatically adding the 6 exterior blocks of the 3D image
    xmin,ymin,zmin = AA(amin)(TRANS(V))
    xmax,ymax,zmax = AA(amax)(TRANS(V))
    exterior_xmin, exterior_xmax, exterior_ymin, exterior_ymax, exterior_zmin, exterior_zmax = [],[],[],[],[],[]
    for (key,value) in verts.items():
        if key[0] == xmin: exterior_xmin.append(value)
        if key[0] == xmax: exterior_xmax.append(value)
        if key[1] == ymin: exterior_ymin.append(value)
        if key[1] == ymax: exterior_ymax.append(value)
        if key[2] == zmin: exterior_zmin.append(value)
        if key[2] == zmax: exterior_zmax.append(value)
    esteriorCells = [exterior_xmin, exterior_xmax, exterior_ymin, exterior_ymax, exterior_zmin, exterior_zmax]
    model = V, F3V + esteriorCells
    return model

if __name__=="__main__":

    blocks3D = [ [[0,0,0],[5,10,3]], [[5,0,0],[9,3,3]], [[9,0,0],[13,3,3]], [[5,3,0],[8,10,3]],  [[8,3,0],[13,10,3]], [[0,10,0],[9,12,3]], [[9,10,0],[13,12,3]] ]
    
    blocks = [ CAT([ block[0],VECTDIFF(REVERSE(block)) ])  for block in blocks3D ]
    model = lar3DFromImageBlocks(blocks)
    V,faces = larSkeletons(model,dim=3)
    F0V, F1V, F2V, F3V = faces
    VIEW(EXPLODE(1.2,1.2,1.2)( MKPOLS((V,F3V[:-6])) ))
    VIEW(EXPLODE(1.2,1.2,1.2)( MKPOLS((V,F2V)) ))
    VIEW(EXPLODE(1.2,1.2,1.2)( MKPOLS((V,F1V)) ))
    VIEW(EXPLODE(1.2,1.2,1.2)( MKPOLS((V,F0V+F1V+F2V+F3V[:-6])) ))

    boundary_3 = larBoundary(F2V,F3V[:-6])
    chain_2 = larBoundaryChain(boundary_3,range(len(F3V[:-6])))
    boundary_faces = csrChainToCellList(chain_2)
    faces = [F2V[f] for f in boundary_faces]
    VIEW(EXPLODE(1.2,1.2,1.2)( MKPOLS((V,faces)) ))
'''

#------------------------------------------------------------------
#--application layer (demo)----------------------------------------
#------------------------------------------------------------------
'''
if __name__ == "__main__" and False:
    
    # input of topology and geometry
    V = [[5.,29.],[17.,29.],[8.,25.],[11.,25.],[14.,25.],
         [ 0.,23.], [5.,23.],[17.,23.],[27.,23.],[0.,20.],
         [5.,20.],[8.,19.],[11.,19.],[11.,17.],[14.,17.],[0.,16.],
         [5.,16.],[14.,16.],[17.,16.],[23.,16.],[0.,10.],
         [14.,10.],[23.,10.],[27.,10.],[0.,6.],[5.,6.],[5.,3.],
         [20.,3.],[23.,3.],[20.,0.],[27.,0.]]
    
    EV = [[5,6,0,1,7],[7,18],[18,17],[17,21,20],
          [20,15,16,10,9,5], [12,11,2,3],[3,4,14,13,12],[7,8,23],[22,23],
          [22,19,18],[22,28,27],[26,27],[26,25,24,20],[23,30,29,27]]
    
    FV = [[0,1,2,3,4,5,6,7,9,10,11,12,13,14,15,16,17,18,20,21],
          [7,8,18,19,22,23],[17,18,19,20,21,22,24,25,26,27,28],
          [22,23,27,28,29,30]]
    
    
    # characteristic matrices
    csrFV = csrCreate(FV)
    csrEV = csrCreate(EV)
    print "\nFV =\n", csrToMatrixRepresentation(csrFV)
    print "\nEV =\n", csrToMatrixRepresentation(csrEV)
    
    # transposition
    csrVF = csrTranspose(csrFV)
    print "\nFV.T =\n", csrToMatrixRepresentation(csrVF)
    
    # product
    csrEF = matrixProduct(csrEV, csrVF)
    print "\nEF =\n", csrToMatrixRepresentation(csrEF)
    
    # product and transposition
    csrFE = csrTranspose(csrEF)
    print "\nFE =\n", csrToMatrixRepresentation(csrFE)
    
    
    # boundary and coboundary operators
    facetLengths = [csrCell.getnnz() for csrCell in csrEV]
    boundary = csrBoundaryFilter(csrEF,facetLengths)
    coboundary = csrTranspose(boundary)
    print "\ncoboundary =\n", csrToMatrixRepresentation(coboundary)
    
    
    # boundary 1-chains (edge numerals) of unit 2-chains (i.e. 2-cells)
    boundary_2_Op = boundary
    _2cells = csrExtractAllGenerators(boundary_2_Op)
    print "\n_2cells =\n", _2cells
    
    
    # boundary 0-chains (vertex numerals) of unit 1-chains (i.e. 1-cells)
    boundary_1_Op = csrTranspose(csrEV)
    _1cells = csrExtractAllGenerators(boundary_1_Op)
    print "\n_1cells =\n", _1cells
    
    
    # 2D polygon complex
    polygons2D = [STRUCT([ POLYLINE([V[v]
                                     for v in EV[edge]]) for edge in cell])
                  for cell in _2cells]
    VIEW(EXPLODE(1.2,1.2,1)(polygons2D))
    
    
    # 2D curved cell complex
    cells2D = [SOLIDIFY(STRUCT([ bezier([V[v] for v in EV[edge]])
                                for edge in cell]))
               for cell in _2cells]
    
    _2Dmodel = (V,[[[v for v in EV[edge]] for edge in cell] for cell in _2cells])
    
    VIEW(EXPLODE(1.2,1.2,1)(cells2D))
    colors = [RED,GREEN,BLUE,YELLOW,CYAN,MAGENTA,WHITE,GRAY,BLACK]
    VIEW(STRUCT([COLOR(colors[k % 9])(cell) for k,cell in enumerate(cells2D)]))
    
    
    # csr column representation of the total (row-)chain
    total_2_chain = csrCreateTotalChain(csrGetNumberOfRows(csrFV))
    print "\ntotal_2_chain =\n", csrChainToCellList(total_2_chain)
    
    
    # boundary 1-chain computation
    boundary_1_chain = csrBinFilter( matrixProduct(boundary, total_2_chain) )
    boundary_1_cells = csrChainToCellList( boundary_1_chain )
    print "\nboundary_1_cells =\n",boundary_1_cells
    
    
    # boundary 1-chain visualization
    boundary1D = AA(bezier)([[V[v] for v in EV[e]]
                             for e in boundary_1_cells ])
    VIEW(STRUCT(boundary1D))
    
    
    # computation of interior 1-cells
    interior_1_cells = [k for k in range(len(EV))
                        if k not in boundary_1_cells]
    print "\ninterior_1_cells =\n", interior_1_cells
    
    
    
    # visualization of interior 1-cells
    interior1D= AA(bezier)([[V[v] for v in EV[e]]
                            for e in interior_1_cells])
    VIEW(STRUCT(AA(COLOR(RED))(boundary1D) +
                cells2D + AA(COLOR(GREEN))(interior1D)))
    
    
    # computation of a 0-complex
    V_0 = [[0.],[5.],[10.],[15.],[20.]]
    VV_0 = AA(LIST)(range(len(V_0))) # [[0],[1],[2],[3],[4]]
    cells0D = AA(MK)([V_0[v[0]] for v in VV_0])
    floors2D = AA(PROD)(CART([cells2D,cells0D]))
    VIEW(EXPLODE(1.2,1.2,1.5)(floors2D))
    
    
    # computation of a 1-complex
    EV_1 = [[0,1],[1,2],[2,3],[3,4]]
    csrEV_1 = csrCreateFromCoo(cooCreateFromBrc(EV_1))
    csrVE_1 = csrTranspose(csrEV_1)
    boundary1 = csrVE_1   # by def: max(VE_1[K]) == 1.
    print "\nboundary1 =\n", csrToMatrixRepresentation(boundary1)
    
    
    # 1D cell complex
    total_1_chain = csrCreateTotalChain(csrGetNumberOfRows(csrEV_1))
    print "\ntotal_1_chain =\n", total_1_chain
    cells1D = [ POLYLINE([ V_0[v] for v in edge ]) for edge in EV_1 ]
    VIEW(EXPLODE(2,2,2)(cells1D))
    
    
    # Cartesian product complexes
    boundary2D=AA(PROD)(CART([boundary1D,cells1D]))
    interior2D=AA(PROD)(CART([interior1D,cells1D]))
    VIEW(EXPLODE(1.1,1.1,1.5)(interior2D + floors2D))
    solid3D = AA(PROD)(CART([cells2D,cells1D]))
    VIEW(EXPLODE(1.1,1.1,1.5)(solid3D))
    boundary3D = boundary2D + floors2D
    VIEW(EXPLODE(1.1,1.1,1.5)(boundary3D))
'''