#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
#  combine_test.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2013-07-09.
#  Copyright 2013 Alexander Rudy. All rights reserved.
# 


from __future__ import (absolute_import, unicode_literals, division,
                        print_function)


import numpy as np

import matplotlib.pyplot as plt

image_cube = np.random.rand(10,200,200)

print("Starting")
import combine_py
image = combine_py.maskcombine(image_cube)
print("Done")
plt.imshow(image, interpolation='nearest')
plt.colorbar()
plt.show()