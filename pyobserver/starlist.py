# -*- coding: utf-8 -*-
# 
#  starlist.py
#  Starlist Tools
#  pynirc2
#  
#  Created by Jaberwocky on 2013-02-11.
#  Copyright 2013 Jaberwocky. All rights reserved.
# 
"""
:mod:`starlist` - Conversion from Starlist to region and back!
==============================================================

This module implements the :program:`PO slds9` command.

"""
from pyshell.subcommand import SCEngine

from datetime import date, datetime
import os.path
from textwrap import fill
import warnings

import pyshell.util

pyshell.util.ipydb()

from .util import parse_starlist

class StarlistToRegion(SCEngine):
    """Convert a starlist to a ds9 region"""
    
    description = fill("Simple tool for conversion between a text-based starlist and a DS9 region in WCS. By default, this tool will convert from starlist.txt to starlist.reg")
    help = "Convert a starlist to a ds9 region or vice-versa."
    
    _header = """# Region file format: DS9 version 4.1
global color=green dashlist=8 3 width=1 font="helvetica 10 normal roman" select=1 highlite=1 dash=0 fixed=0 edit=1 move=1 delete=1 include=1 source=1
"""
    
    supercfg = [(__name__,"observing.yml")]
    
    
    command = "slds9"
    
    def before_configure(self):
        """Check for pyregion"""
        super(StarlistToRegion, self).before_configure()
        try:
            import pyregion
        except ImportError:
            self.parser.error("Module 'pyregion' required but not found!")
        try:
            import astropy
        except ImportError:
            self.parser.error("Module 'astropy' required but not found!")
    
    def after_configure(self):
        """Configure and set-up arguments"""
        super(StarlistToRegion, self).after_configure()
        self.parser.add_argument('input',help="region/starlist file name.",nargs="?",action='store',default=self.config["Defaults.Starlist"],metavar=self.config["Defaults.Starlist"])
        self.parser.add_argument('output',help="region/starlist file name.",action='store',nargs="?",default=self.config["Defaults.Region"],metavar=self.config["Defaults.Region"])
        self.parser.add_argument('--coordinates',help="Coordinate system used by the starlist.",action='store',default=self.config["Region.CoordinateSystem"],metavar=self.config["Region.CoordinateSystem"])
        self.parser.add_argument('--radius',help="Region radius (for circle regions)",action='store',default=self.config["Region.Radius"],metavar=self.config["Region.Radius"])
        
    def do(self):
        """Do the actual conversion"""
        if self.config["Region.CoordinateSystem"] != self.opts.coordinates:
            warnings.warn("Only '{!s}' coordinate system is supported currently!".format(self.config["Region.CoordinateSystem"]))
        
        if self.opts.input.endswith(".reg"):
            self.reg2sl()
        elif self.opts.output.endswith(".reg"):
            self.sl2reg()
        else:
            print("Assuming conversion from starlist to region!")
            self.sl2reg()
    
    def sl2reg(self):
        """Convert a starlist to a region file."""
        from astropy.coordinates import FK5
        import astropy.units as u
        print("Converting '{input:s}' starlist to '{output:s}' ds9 region file.".format(**vars(self.opts)))
        self.targets = parse_starlist(self.opts.input)
        with open(self.opts.output,'w') as regionfile:
            regionfile.write(self._header)
            regionfile.write("%s\n" % self.opts.coordinates)
            for target in self.targets:
                target["RA"] = target["Position"].to(FK5).ra.to_string(u.hourangle, sep=":", pad=False)
                target["Dec"] = target["Position"].to(FK5).dec.to_string(u.degree, sep=":", pad=False)
                target["radius"] = self.opts.radius
                keywords = [ "{0}={1}".format(key,value) for key,value in target.items() if key not in ["RA", "Dec", "radius", "Name", "Position" ] ]
                target["keywords"] = " ".join(keywords)
                regionfile.write("circle({RA},{Dec},{radius}) # text={{{Name}}} {keywords:s}\n".format(**target))
            
        
    
    def reg2sl(self):
        """Convert a region file to a starlist."""
        import pyregion
        import astropy.coordinates as coord
        import astropy.units as u
        print("Converting '{input:s}' ds9 region file to '{output:s}' starlist.".format(**vars(self.opts)))
        with open(self.opts.input,'r') as regionfile:
            regions = pyregion.parse(regionfile.read())
        with open(self.opts.output,'w') as starlist:
            for i,region in enumerate(regions):
                
                if region.coord_format != 'fk5':
                    self.log.critical("Coordinate system {!r} unkown!".format(region.coord_format))
                    break
                
                # We only parse circles!
                if region.name == 'circle':
                    
                    # Parse the location
                    ra,dec = region.coord_list[0:2]
                    loc = coord.FK5(ra=ra,dec=dec,unit=(u.degree,u.degree))
                    if "text" in region.attr[1]:
                        name = region.attr[1]["text"]
                    else:
                        name = "Target%d" % i
                    
                    # Handle comments
                    comments = region.comment.split()
                    for comment in comments:
                        if comment.startswith("text={"):
                            comments.remove(comment)
                    
                    # Write out the starlist line
                    starlist.write("{name:<20s} {ra:s} {dec:s} {epoch:.0f} {keywords:s}".format(
                        name = name.strip(),
                        ra = loc.ra.format(u.hour, sep=" ", pad=True),
                        dec = loc.dec.format(sep=" ", alwayssign=True),
                        epoch = loc.equinox.jyear,
                        keywords = " ".join(comments),
                    ))
                    starlist.write("\n")
                else:
                    self.log.warning("Region {!r} not parsed. It is not a circle.".format(region))
                    
        

        

        