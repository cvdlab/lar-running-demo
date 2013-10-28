import dicom
import pylab
from lar import *
from time import time
from copy import copy
from random import random
from scipy import ndimage,sparse,amax,amin,reshape
import numpy as np

    
def quantize (min,max,nparts):
    scalingFact = float(nparts)/(max-min)
    def quantize0 (image):
        row,col = image.shape
        vect = reshape(image,(row*col,))
        vect = AA(int)((vect-min)*scalingFact + 0.5)
        vect = np.array(vect)
        vect = vect/scalingFact + min
        return reshape(vect,(row,col))
    return quantize0



def CTimage2blocks(image):

    # Input of CT image into persistent storage structures

    BLOCKS = []
    Visited = copy(ct.pixel_array)
    for i in range(128):
        for j in range(128):
            Visited[i,j] = 0

    # Initialization of the sparse matrix used as query point storage

    Points = sparse.lil_matrix(csrCreate([range(imWidth) for k in range(imHeight)]), dtype=int)

    def pointSelection(Points):
        indices = np.nonzero(Points)
        nonEmptyRows = list(set(indices[0]))
        numberOfNonEmptyRows = len(nonEmptyRows)
        rowOrdinal = int(numberOfNonEmptyRows * random())
        rowIndex = nonEmptyRows[rowOrdinal]
        numberOfNonZeroElementsInRow = Points[rowIndex,:].nnz
        columnOrdinal = int(numberOfNonZeroElementsInRow * random())
        indices = np.nonzero(Points[rowIndex,:])[1]
        columnIndex = indices[columnOrdinal]
        return rowIndex,columnIndex

    # Generation of a random point

    while True:
    #for k in range(1):
        
        mask0 = scipy.zeros((imWidth,imHeight),dtype=image.dtype)
        mask1 = scipy.zeros((imWidth,imHeight),dtype=image.dtype)
        mask2 = scipy.zeros((imWidth,imHeight),dtype=image.dtype)
        mask3 = scipy.zeros((imWidth,imHeight),dtype=image.dtype)
        mask = scipy.zeros((imWidth,imHeight),dtype=int)
        
        #p = int(imWidth*random()),int(imWidth*random())
        if Points.nnz != 0:
            p = pointSelection(Points)
            #p = (6, 91)
        else: break

        #print "\np =",p
        if Points[p] != 0:
            # reverse p value, in order to show
            Visited[p] = image[p]
            #pylab.imshow(Visited)
            #pylab.show()

            # Computation of the sub-image of a point

            x0,y0 = p
            cross = x0,x0,x0,y0,y0,y0
            while cross != crossGrow(image,cross):
                cross = crossGrow(image,cross)
            xm,x0,xM,ym,y0,yM = cross
            xspan = xm,xM
            yspan = ym,yM
                
            # Draw the computed subimage of the point 
            
            for x in range(xm,xM+1):
                for y in range(ym,yM+1):
                    mask0[x,y] = image[x,y]
            for x in range(xm,xM+1): mask0[x,y0] = image[x,y0]+1000
            for y in range(ym,yM+1): mask0[x0,y] = image[x0,y]+1000
            #pylab.imshow(mask0)
            #pylab.show()
            for x in range(xm,xM+1): mask0[x,y0] = image[x,y0]
            for y in range(ym,yM+1): mask0[x0,y] = image[x0,y]

            # Computation of the 1D bar-charts of the point

            pointValue = image[p]
            x0,y0 = p

            Y0,Y1 = yspan
            for y in range(Y0,Y1+1):
                span = x0,x0,x0,y
                while span != xbar(image,span,xspan):
                    span = xbar(image,span,xspan)
                xm,x,xM,y = span
                # drawing of a span
                for x in range(xm,xM+1): mask1[x,y] = not(mask1[x,y])
            #pylab.imshow(mask1)
            #pylab.show()

            X0,X1 = xspan
            for x in range(X0,X1+1):
                span = x,y0,y0,y0
                while span != ybar(image,span,yspan):
                    span = ybar(image,span,yspan)
                x,ym,y,yM = span
                # drawing of a span
                for y in range(ym,yM+1): mask2[x,y] = not(mask2[x,y])
            #pylab.imshow(mask2)
            #pylab.show()

            # Visible set: intersection of 1D bar-charts of the point

            for x in range(X0,X1+1):
                for y in range(Y0,Y1+1):
                    mask3[x,y] = mask1[x,y] and mask2[x,y]
            #pylab.imshow(mask3)
            #pylab.show()

            # Computation of weights of visible set
            
            x0,y0 = p
            spans = []
            for x in range(X0,X1+1):
                span = x,y0,y0,y0
                while span != ybar(mask3,span,yspan):
                    span = ybar(mask3,span,yspan)
                spans += [span]
            
            for span in spans:
                x,ym,y,yM = span
                for y in range(ym,yM+1):
                    mask[x,y] = delta(p,(x,y))

            #print "\nmask =\n", mask[X0:(X1+1),Y0:(Y1+1)]


            # Sorting pixels of visible subregions
            
            def sortVisible(p,xspan,yspan):
                subregions = []
                (x0,y0),(X0,X1),(Y0,Y1) = p,xspan,yspan
                subregions = []
                subregion = []
                for x in range(X0,x0+1):
                    for y in range(Y0,y0+1):
                        subregion += [[mask[x,y],x,y]]
                subregions += [sorted(subregion,reverse=True)[0]]
                subregion = []
                for x in range(x0,X1+1):
                    for y in range(Y0,y0+1):
                        subregion += [[mask[x,y],x,y]]
                subregions += [sorted(subregion,reverse=True)[0]]
                subregion = []
                for x in range(X0,x0+1):
                    for y in range(y0,Y1+1):
                        subregion += [[mask[x,y],x,y]]
                subregions += [sorted(subregion,reverse=True)[0]]
                subregion = []
                for x in range(x0,X1+1):
                    for y in range(y0,Y1+1):
                        subregion += [[mask[x,y],x,y]]
                subregions += [sorted(subregion,reverse=True)[0]]
                return subregions
            
            subregions = sortVisible(p,xspan,yspan)
            
            # block generation (with corrections to eliminate the pixel area)
            # [check border conditions:  possible BUG]
            
            x00,y00 = subregions[0][1:]
            x10,y10 = subregions[1][1:]
            x10 = x10+1
            x01,y01 = subregions[2][1:]
            y01 = y01+1
            x11,y11 = subregions[3][1:]
            x11,y11 = x11+1,y11+1
            
            # modify position for pixel origin, to maximize cross covering
            def pixelOrigin(x0,y0, x00,y00, x10,y10, x01,y01, x11,y11):
                def area (x0,y0):
                    return abs((x00-x0)*(y00-y0) + (x10-x0)*(y10-y0) + (x01-x0)*(y01-y0) + (x11-x0)*(y11-y0))
                areas  = [ (area(x0,y0), (x0,y0)) ]
                areas += [ (area(x0+1,y0), (x0+1,y0)) ]
                areas += [ (area(x0,y0+1), (x0,y0+1)) ]
                areas += [ (area(x0+1,y0+1), (x0+1,y0+1)) ]
                best = sorted(areas)[-1]
                x0,y0 = best[1]
                return x0,y0
            
            x0,y0 = pixelOrigin(x0,y0, x00,y00, x10,y10, x01,y01, x11,y11)
            
            dx00,dy00 = AA(abs)(VECTDIFF([(x00,y00),(x0,y0)]))
            dx10,dy10 = AA(abs)(VECTDIFF([(x10,y10),(x0,y0)]))
            dx01,dy01 = AA(abs)(VECTDIFF([(x01,y01),(x0,y0)]))
            dx11,dy11 = AA(abs)(VECTDIFF([(x11,y11),(x0,y0)]))
            
            block00 = [x00,y00] + [dx00,dy00]
            block10 = [x0,y10] + [dx10,dy10]
            block01 = [x01,y0] + [dx01,dy01]
            block11 = [x0,y0] + [dx11,dy11]

            #print "\nblock00,block01,block10,block11 =", (block00,block10,block01,block11)

            # possible joins of the four blocks (Block = [x,y,dx,dy])

            """
                if 0010 and 0111 and 0001 and 1011: A
                elif 0010 and 0111: B
                elif 0010: D
                elif 0111: E
                elif 0001 and 1011: C
                elif 0001: F
                elif 1011: G
                else H
                """
            pred_0010 = block00[3] == block10[3]
            pred_0111 = block01[3] == block11[3]
            pred_0001 = block00[2] == block01[2]
            pred_1011 = block10[2] == block11[2]

            block_A = copy(block00)
            block_A[2] = block00[2] + block10[2]
            block_A[3] = block00[3] + block01[3]
            block_a = copy(block00)
            block_a[2] = block00[2] + block10[2]
            block_b = copy(block01)
            block_b[2] = block01[2] + block11[2]
            block_c = copy(block00)
            block_c[3] = block00[3] + block01[3]
            block_d = copy(block10)
            block_d[3] = block10[3] + block11[3]

            blocks = []
            if pred_0010 and pred_0111 and pred_0001 and pred_1011:
                blocks = [block_A]
            else:
                if pred_0010 and pred_0111:
                    blocks = [block_a,block_b]
                elif pred_0001 and pred_1011:
                    blocks = [block_c,block_d]
                
                else:
                    if blocks == [] and pred_0010:
                        blocks = [block_a,block01,block11]
                    elif blocks == [] and pred_0111:
                        [block_b,block00,block10]
                    
                    elif blocks == [] and pred_0001:
                        blocks = [block_c,block10,block11]
                    elif blocks == [] and pred_1011:
                        blocks = [block_d,block00,block01]

            if blocks == []: blocks = [block00,block10,block01,block11]

            # filter out empty boxes

            blocks = [ block for block in blocks if not( block[2]==0 or block[3]==0) ]

            #print "\nblocks =", blocks

            # store current blocks in persistent data structures

            def fill(store,block):
                x0,y0,dx,dy = block
                for x in range(x0,x0+dx):
                    for y in range(y0,y0+dy):
                        store[x,y] = image[x,y]
                        Points[x,y] = 0
                return store

            BLOCKS += blocks
            for block in blocks:
                Visited = fill(Visited,block)

    return BLOCKS

if __name__ == "__main__":

    # image input

    ct = dicom.read_file("CT_small.dcm")
    image = copy(ct.pixel_array)
    imWidth,imHeight = image.shape
    pylab.imshow(image, cmap=pylab.cm.bone)
    pylab.show()

    image = quantize (amin(image),amax(image),16)(image)
    pylab.imshow(image)
    pylab.show()

    # print computing time

    start = time()
    BLOCKS = CTimage2blocks(image)
    end = time() 
    print "\ntime =", end - start
    print "len(BLOCKS) =",len(BLOCKS), "\n"

    # display current blocks in pyPlasm
    
    highestColor = amax(image)

    def block(data):
        x,y,dx,dy = AA(float)(data)
        color = Color4f(pylab.cm.rainbow.__call__(image[x,y]/highestColor))
        rectangle = CUBOID([dx,dy])
        return T([1,2])([x,y])(COLOR(color)(PROD([rectangle,Q(1)])))

    solids = AA(block)(BLOCKS)

    View(STRUCT(solids))
    VIEW(EXPLODE(2,2,2)(solids))
    #print "\nBLOCKS =",BLOCKS

if __name__ == "__main__":

    # image decomposition at pixel level

    BLOCKS = [[x,y,1,1]  for x in range(imWidth) for y in range(imHeight)]

    solids = AA(block)(BLOCKS)
    View(STRUCT(solids))
    VIEW(EXPLODE(2,2,2)(solids))
