# -*- coding: utf-8 -*-
# 
#  util.py
#  pynirc2
#  
#  Created by Jaberwocky on 2013-02-11.
#  Copyright 2013 Jaberwocky. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division, print_function)


def stream_less(infunc):
    """Launch the terminal command `less` using an input stream."""
    import subprocess, sys
    
    args = ['less','-e']
    
    less = subprocess.Popen(args,stdin=subprocess.PIPE)
    try:
        infunc(less.stdin)
        less.stdin.flush()
        less.stdin = sys.stdin
        less.wait()
    except IOError:
        less.terminate()
        raise
    