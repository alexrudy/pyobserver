# -*- coding: utf-8 -*-
# 
#  util.py
#  pynirc2
#  
#  Created by Jaberwocky on 2013-02-11.
#  Copyright 2013 Jaberwocky. All rights reserved.
# 

def parse_starlist(starlist):
    """Parse a starlist into a sequence of dictionaries."""
    output = []
    with open(starlist,'r') as stream:
        starlist = stream.readlines()
    for line in starlist:
        if line.startswith("#"):
            continue
        d = {}
        parts = line.split()
        d["name"] = parts[0]
        d["ra"] = " ".join(parts[1:4])
        d["dec"] = " ".join(parts[4:7])
        d["epoch"] = parts[7]
        for part in parts[8:]:
            split = part.split("=")
            if len(split) == 2:
                key,value = split
                d[key] = value
        output.append(d)
    return output
    
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
    