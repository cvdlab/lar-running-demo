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
import sys
import logging
from scipy import zeros,arange,mat
from scipy.sparse import *
from scipy.spatial import Delaunay
from scipy.linalg import *
from pyplasm import *

try: import simplejson as json
except ImportError: import json
import requests
from numpy import *
from termcolor import colored

logging.basicConfig(format='%(levelname)s [%(filename)s, %(funcName)s] >> %(message)s', level=logging.INFO)

url = "http://cvd01.dia.uniroma3.it:3000/multiply";

def csrToJSON(CSRm):

    if (not isspmatrix_csr(CSRm)):
        raise Exception('Matrix is not in CSR format')

    ROWCOUNT = CSRm.shape[0];
    COLCOUNT = CSRm.shape[1];
    ROW = CSRm.indptr.tolist();
    COL = CSRm.indices.tolist();
    DATA = CSRm.data.tolist();
    JSONm = json.dumps({"ROWCOUNT":ROWCOUNT, "COLCOUNT":COLCOUNT, "ROW":ROW, "COL":COL, "DATA":DATA })

    logging.debug('CSRm.todense(): ' + str(CSRm.todense()));
    logging.info('ROWCOUNT: ' + str(ROWCOUNT));
    logging.info('COLCOUNT: ' + str(COLCOUNT));
    logging.info('ROW: ' + str(ROW));
    logging.info('COL: ' + str(COL));
    logging.info('DATA: ' + str(DATA));

    return JSONm

def jsonToCSR(JSONm):

    ROWCOUNT = JSONm['ROWCOUNT'];
    COLCOUNT = JSONm['COLCOUNT'];
    ROW = JSONm['ROW'];
    COL = JSONm['COL'];
    DATA = JSONm['DATA'];
    CSRm = csr_matrix((array(DATA),array(COL),array(ROW)),shape=(ROWCOUNT,COLCOUNT));

    if (not isspmatrix_csr(CSRm)):
        raise Exception('Matrix is not in CSR format')

    logging.debug('CSRm.todense(): ' + str(CSRm.todense()));
    logging.info('ROWCOUNT: ' + str(ROWCOUNT));
    logging.info('COLCOUNT: ' + str(COLCOUNT));
    logging.info('ROW: ' + str(ROW));
    logging.info('COL: ' + str(COL));
    logging.info('DATA: ' + str(DATA));
    
    return CSRm;

def csrTranspose(CSRm):
    CSRm = CSRm.T
    return CSRm
    
def matrixProduct(A,B):

# Input parameters check

    if (not isspmatrix(A)):
        raise Exception('A is not a scipy matrix')
    if (not isspmatrix(B)):
        raise Exception('B is not a scipy matrix')
    if (not (A.shape[1] == B.shape[0])):
        raise Exception('Column of matrix A are not equal to raws of matrix B')

# Convert to JSON

    logging.info('Matrix A');
    Ajson = csrToJSON(A.tocsr());
    
    logging.info('Matrix B');
    Bjson = csrToJSON(B.tocsr()); 

# Send A and B, Receive A*B

    payload = {"matrixa": Ajson, "matrixb": Bjson};   

    req = requests.post(url, data=payload);
    logging.info('Matrix A and matrix B sent');
    logging.info('Status code: ' + str(req.status_code));
    logging.info('Url: ' + str(req.url));
    logging.info('Headers: ' + req.headers['Content-Type']);
#    logging.debug('Content: ' + str(req.content));

    ABjson = json.loads(req.content);
    logging.info('Matrix A*B received');

# Convert to CSR

    logging.info('Matrix AB');
    AB = jsonToCSR(ABjson);

# Output parameters check

    if (not isspmatrix(AB)):
        raise Exception('A*B is not a scipy matrix');
    if (not ((AB.shape[0] == A.shape[0]) and (AB.shape[1] == B.shape[1]))):
        raise Exception('Output matrix A*B dimensions are not compatible with input matrices A,B dimensions');

    return AB
