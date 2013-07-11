# -*- coding: utf-8 -*-
# 
#  combine.pyx
#  pyobserver
#  
#  Created by Alexander Rudy on 2013-07-09.
#  Copyright 2013 Alexander Rudy. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division, print_function)

import  numpy as np
cimport numpy as np

cdef np.ndarray[np.float_t, ndim=3] maskcombine(np.ndarray[np.float_t, ndim=3] cube not None, np.ndarray[np.float_t, ndim=3] mcube not None):
    
    cdef int xmax = cube.shape[1]
    cdef int ymax = cube.shape[2]
    
    cdef np.ndarray image = np.zeros([xmax, ymax], dtype=np.float)
    
    cdef int x, y
    
    for x in range(xmax):
        for y in range(ymax):
            mask = mcube[i,j]