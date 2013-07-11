# -*- coding: utf-8 -*-
# 
#  combine_py.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2013-07-09.
#  Copyright 2013 Alexander Rudy. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)


from __future__ import (absolute_import, unicode_literals, division, print_function)

import numpy as np

def maskcombine(cube,mcube=None,function=np.median,axis=0):
    """Combine everything!"""
    rmask = True
    if cube.ndim != 3:
        raise ValueError("Cubes must have 3 dimensions!")
    if mcube is None:
        rmask = False
        mcube = np.zeros(cube.shape, dtype=np.int)
    if mcube.shape != cube.shape:
        raise ValueError("Mask and Cube must match shapes!")
    
    shape = list(cube.shape)
    del shape[axis]
    
    cube = np.rollaxis(cube, axis)
    mcube = np.rollaxis(mcube, axis)
    
    image = np.empty(shape, dtype=np.float)
    mimage = np.empty(shape, dtype=np.int)
    
    for i in range(shape[0]):
        for j in range(shape[1]):
            mask = mcube[:,i,j] == 0
            if np.sum(mask) == 0:
                image[i,j] = 0.0
                mimage[i,j] = 1.0
            else:
                image[i,j] = function( cube[:,i,j][mask] )
                mimage[i,j] = 0.0
                
    if rmask:
        return image, mimage
    return image
            
            