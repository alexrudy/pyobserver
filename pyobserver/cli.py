# -*- coding: utf-8 -*-
# 
#  cli.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2013-04-19.
#  Copyright 2013 Alexander Rudy. All rights reserved.
# 

from pyshell.subcommand import SCController
from .fitsfiles import FITSGroup, FITSLog, FITSList, FITSInfo, FITSInspect
from .starlist import StarlistToRegion

class POcommand(SCController):
    
    description = "Observing and FITS file inspection tools."
    
    defaultcfg = "observing.yml"
    
    _subparsers_help = "Available Commands:"
    
    subEngines = [
        FITSGroup,
        FITSLog,
        FITSList,
        FITSInfo,
        FITSInspect,
        StarlistToRegion,
    ]