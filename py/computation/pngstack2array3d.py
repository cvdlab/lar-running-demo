"""
To import a stack of PNG images into a 3D array, with denoising and color quatization.

Return a scipy ndarray.
"""
import sys
import numpy as np
from numpy import reshape,array
from scipy.cluster.vq import kmeans,vq
import png
import matplotlib.pyplot as plt
from scipy import ndimage
import struct
import os

# Default is 10
NOISE_SHAPE_DETECT=10

def getImageData(fileName):
	def get_image_info(data):
		if is_png(data):
			w, h = struct.unpack('>LL', data[16:24])
			width = int(w)
			height = int(h)
		else:
			raise Exception('not a png image')
		return width, height


	def is_png(data):
		return (data[:8] == '\211PNG\r\n\032\n'and (data[12:16] == 'IHDR'))
		
	with open(fileName, 'rb') as f:
		data = f.read()
		
	return get_image_info(data)


def centroidcalc(path, IMAGE, colors):
	"""
	To import a stack of PNG images into a 3D array, with denoising and color quatization.
	
	path = the path to the directory of images
	MIN_SLICE, MAX_SLICE = the numbers of first and last slice.
	Return a scipy ndarray.
	"""

	# -----------------------------------------------------------------------------
	# import images in a 3D array -------------------------------------------------
	# -----------------------------------------------------------------------------
	image2d = []
	filename = path+str(IMAGE)+'.png'

	r=png.Reader(filename)
	content = r.read()
	page = [list(row) for k,row in enumerate(content[2])]
	image2d.append(page)
	
	image3d = array(image2d,dtype='uint8')

	# -----------------------------------------------------------------------------
	# selecting colors for quantization, via clustering on first image ------------
	# -----------------------------------------------------------------------------
	#denoise before selection
	# image3d[0] = ndimage.median_filter(image3d[0], NOISE_SHAPE_DETECT)
	
	# reshaping the pixels matrix
	pixel = reshape(image3d[0],(image3d[0].shape[0]*image3d[0].shape[1],1))
	# performing the clustering
	centroids,_ = kmeans(pixel,colors) # "colors" colors will be found

	return pixel,centroids
	
def pngstack2array3d(path, MIN_SLICE, MAX_SLICE, colors, pixel, centroids):
	"""
	To import a stack of PNG images into a 3D array, with denoising and color quatization.
	
	path = the path to the directory of images
	MIN_SLICE, MAX_SLICE = the numbers of first and last slice.
	Return a scipy ndarray.
	"""

	# -----------------------------------------------------------------------------
	# import images in a 3D array -------------------------------------------------
	# -----------------------------------------------------------------------------
	image2d = []
	for slice in range(MIN_SLICE, MAX_SLICE):
		filename = path+str(slice)+'.png'
		r=png.Reader(filename)
		content = r.read()
		page = [list(row) for k,row in enumerate(content[2])]
		image2d.append(page)
	
	image3d = array(image2d,dtype='uint8')

	# -----------------------------------------------------------------------------
	# -----------------------------------------------------------------------------
	# -----------------------------------------------------------------------------

	for page in xrange(image3d.shape[0]):

		# image denoising 
		# -------------------------------------------------------------------------
		image3d[page] = ndimage.median_filter(image3d[page], NOISE_SHAPE_DETECT)

		# field quantization 
		# -------------------------------------------------------------------------
		# reshaping the pixels matrix
		pixel = reshape(image3d[page],(image3d[page].shape[0]*image3d[page].shape[1],1))
		# quantization
		qnt,_ = vq(pixel,centroids)
		# reshaping the result of the quantization
		centers_idx = np.reshape(qnt,image3d[page].shape)
		image3d[page] = centroids[centers_idx].reshape(image3d[page].shape)

	# Show result
	if False:
		plt.imshow(image3d[0])
		plt.show()
		plt.imshow(image3d[len(image3d)-1])
		plt.show()
	
	# return a scipy ndarray 
	# -------------------------------------------------------------------------
	return image3d,colors,centroids