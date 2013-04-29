# -*- coding: utf-8 -*-
# 
#  starlist.py
#  Starlist Tools
#  pynirc2
#  
#  Created by Jaberwocky on 2013-02-11.
#  Copyright 2013 Jaberwocky. All rights reserved.
# 

from pyshell.subcommand import SCEngine
from datetime import date, datetime
import os.path

from .util import parse_starlist

class StarlistToRegion(SCEngine):
    """Convert a starlist to a ds9 region"""
    
    description = "Simple tool for conversion between a text-based starlist and a DS9 region in WCS."
    help = "Convert a starlist to a ds9 region"
    
    _header = """# Region file format: DS9 version 4.1
global color=green dashlist=8 3 width=1 font="helvetica 10 normal roman" select=1 highlite=1 dash=0 fixed=0 edit=1 move=1 delete=1 include=1 source=1
"""
    
    supercfg = [(__name__,"observing.yml")]
    
    def __init__(self, command='sl2reg'):
        super(StarlistToRegion, self).__init__(command=command)
        
    def configure(self):
        """Configure and set-up arguments"""
        super(StarlistToRegion, self).configure()
        self.parser.add_argument('starlist',help="stalist file name.",nargs="?",action='store',default=self.config["Defaults.Starlist"],metavar=self.config["Defaults.Starlist"])
        self.parser.add_argument('region',help="region file name.",action='store',nargs="?",default=self.config["Defaults.Region"],metavar=self.config["Defaults.Region"])
        self.parser.add_argument('--coordinates',help="coordinate system",action='store',default=self.config["Region.CoordinateSystem"],metavar=self.config["Region.CoordinateSystem"])
        
    def start(self):
        """Configure the conversion."""
        pass
        
    def do(self):
        """Do the actual conversion"""
        self.targets = parse_starlist(self.opts.starlist)
        with open(self.opts.region,'w') as regionfile:
            regionfile.write(self._header)
            regionfile.write("%s\n" % self.opts.coordinates)
            for target in self.targets:
                target["ra"] = ":".join(target["ra"].split())
                target["dec"] = ":".join(target["dec"].split())
                target["radius"] = self.config["Region.Radius"]
                regionfile.write("circle({ra},{dec},{radius}) # text={{{name}}}\n".format(**target))
        
    def end(self):
        """End the program"""
        pass
        
class CoordsToRegion(SCEngine):
    """Convert a starlist to a ds9 region"""
    
    help = "Convert a starlist to a ds9 region"
    
    _header = """# Region file format: DS9 version 4.1
global color=green dashlist=8 3 width=1 font="helvetica 10 normal roman" select=1 highlite=1 dash=0 fixed=0 edit=1 move=1 delete=1 include=1 source=1
"""
    
    supercfg = [(__name__,"observing.yml")]
    
    def __init__(self, command='sl2reg'):
        super(CoordsToRegion, self).__init__(command=command)
        
    def configure(self):
        """Configure and set-up arguments"""
        super(CoordsToRegion, self).configure()
        self.parser.add_argument('coordinates',help="coordinate file name.",nargs=2,action='store',default=self.config["Defaults.Starlist"],metavar=self.config["Defaults.Starlist"])
        self.parser.add_argument('region',help="region file name.",action='store',nargs="?",default=self.config["Defaults.Region"],metavar=self.config["Defaults.Region"])
        self.parser.add_argument('--coordinates',help="coordinate system",action='store',default="image",metavar=self.config["Region.CoordinateSystem"])
        
    def start(self):
        """Configure the conversion."""
        pass
        
    def do(self):
        """Do the actual conversion"""
        with open(self.opts.coordlist, 'w') as targetfile:
            pass
        with open(self.opts.region,'w') as regionfile:
            regionfile.write(self._header)
            regionfile.write("%s\n" % self.opts.coordinates)
            for target in self.targets:
                target["ra"] = ":".join(target["ra"].split())
                target["dec"] = ":".join(target["dec"].split())
                target["radius"] = self.config["Region.Radius"]
                regionfile.write("circle({ra},{dec},{radius}) # text={{{name}}}\n".format(**target))
        
    def end(self):
        """End the program"""
        pass
        