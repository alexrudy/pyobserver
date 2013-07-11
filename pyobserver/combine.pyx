# -*- coding: utf-8 -*-
# 
#  combine.pyx
#  pyobserver
#  
#  Created by Alexander Rudy on 2013-07-09.
#  Copyright 2013 Alexander Rudy. All rights reserved.
# 

# from __future__ import (absolute_import, unicode_literals, division, print_function)

import  numpy as np
cimport numpy as np

def maskcombine(np.ndarray[np.float_t, ndim=3] cube not None, np.ndarray[np.float_t, ndim=3] mcube not None):
    
    cdef int xmax = cube.shape[1]
    cdef int ymax = cube.shape[2]
    cdef np.ndarray image = np.zeros([xmax, ymax], dtype=np.float)
    cdef int x, y, nmask, z, zsum
    cdef np.float tot
    
    for x in range(xmax):
        for y in range(ymax):
            nmask = len(mcube[x,y])
            tot = 0.0
            zsum = 0
            for z in range(nmask):
                if mcube[z,x,y] == 0:
                    tot = tot + cube[z,x,y]
                    zsum = zsum + 1
            image[x,y] = tot / zsum
    return image
                    