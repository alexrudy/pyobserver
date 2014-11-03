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

import os.path
from textwrap import fill
import warnings
from datetime import date, datetime

import astropy.units as u
import astropy.time
from astropy.coordinates import SkyCoord, FK4, FK5, AltAz

import re
_starlist_re_raw = r"""
    ^(?P<Name>.{1,15})[\s]+ # Target name must be the first 15 characters.
    (?P<RA>(?:[\d]{1,2}[\s:][\s\d]?[\d][\s:][\s\d]?[\d](?:\.[\d]+)?)|(?:[\d]+\.[\d]+))[\s]+  # Right Ascension, HH MM SS.SS+
    (?P<Dec>(?:[+-]?[\d]{1,2}[\s:][\s\d]?[\d][\s:][\s\d]?[\d](?:\.[\d]+)?)|(?:[\d]+\.[\d]+)) # Declination, (-)DD MM SS.SS+
    (?:[\s]+(?P<Equinox>(?:[\d]{4}(?:\.[\d]+)?)|(?:APP)))?[\s]* # Equinox.
    (?P<Keywords>.+)?$ # Everything else must be a keyword.
    """
    
_starlist_re = re.compile(_starlist_re_raw, re.VERBOSE)

_starlist_re_strict = r"""
    ^(?P<Name>.{15})\  # Target name must be the first 15 characters.
    (?P<RA>[\d]{2}\ [\d]{2}\ [\d]{2}(?:\.[\d]+)?)\   # Right Ascension, HH MM SS.SS+
    (?P<Dec>[+-]?[\d]{1,2}\ [\d]{2}\ [\d]{2}(?:\.[\d]+)?)\  # Declination, (-)DD MM SS.SS+
    (?P<Equinox>(?:[\d]{4}(?:\.[\d]+)?)|(?:APP))[\ ]? # Equinox.
    (?P<Keywords>[^\ ].+)?$ # Everything else must be a keyword.
    """

_starlist_token_parts = ["Name", "RA", "Dec", "Equinox", "Keywords"]

def verify_starlist_line(text, identifier="<stream line 0>", warning=False):
    """Verify that the given line is a valid starlist."""
    line = text
    messages = []
    match = _starlist_re.match(text)
    if not match:
        raise ValueError("Couldn't parse '{0:s}', no regular expression match found.".format(text))
    data = match.groupdict("")
    
    # Check the Name:
    name_length = match.end('Name') - match.start('Name') + 1
    if name_length < 15:
        messages.append(('Warning','Name','Name should be exactly 15 characters long (whitespace is ok.) len(Name)={0:d}'.format(name_length)))
    
    # Check the RA starting position.
    if match.start('RA') + 1 != 17:
        messages.append(('Error','RA','RA must start in column 17. Start: {0:d}'.format(match.start('RA')+1)))
    
    # Check the Dec starting token
    if match.start('Dec') - match.end('RA') != 1:
        messages.append(('Warning','Dec','RA and Dec should be separated by only a single space, found {0:d} characters.'.format(match.start('Dec') - match.end('RA'))))
    
    # Check the Equinox starting token.
    if match.start('Equinox') - match.end('Dec') != 1:
        messages.append(('Warning','Equinox','Dec and Equinox should be separated by only a single space, found {0:d} characters.'.format(match.start('Equinox') - match.end('Dec'))))
    
    if match.group("Keywords") and len(match.group("Keywords")):
        for kwarg in match.group("Keywords").split():
            if kwarg.count("=") < 1:
                messages.append(('Error', 'Keywords', 'Each keyword/value pair must have 1 "=", none found {!r}'.format(kwarg)))
            if kwarg.count("=") > 1:
                messages.append(('Error', 'Keywords', 'Each keyword/value pair must have 1 "=", {0:d} found {1!r}'.format(kwarg.count("="), kwarg)))
    
    for severity, token, message in messages:
        composed_message = "[{0}][{1} {2}] {3}".format(severity, identifier, token, message)
        if warning:
            warnings.warn(composed_message)
        else:
            print(composed_message)
    

def parse_starlist_line(text):
    """Parse a single line from a Keck formatted starlist, returning a dictionary of parsed values.
    
    :param text: The starlist text line.
    :returns: A dictionary of starlist object properties, set from teh starlist line.
    :raises: ValueError if the line couldn't be parsed.
    
    This function parses a single line from a starlist and returns a dictionary of items from that line. The followig keys are included:
    - `Name`: The target name.
    - `Position`: An astropy.coordinates object representing this position.
    - Any other keyword/value pairs, which are found at the end of the starlist line, and formatted as ``keyword=value``
    
    """
    match = _starlist_re.match(text)
    if not match:
        raise ValueError("Couldn't parse '{}', no regular expression match found.".format(text))
    data = match.groupdict("")
    if data.get('Equinox','') == '':
        equinox = astropy.time.Time.now()
        frame = AltAz
    elif data['Equinox'] == "APP":
        equinox = astropy.time.Time.now()
        frame = 'fk5'
    else:
        equinox = astropy.time.Time(float(data['Equinox']), format='jyear', scale='utc')
        if float(data['Equinox']) <= 1950:
            equinox = astropy.time.Time(float(data['Equinox']), format='byear', scale='utc')
            frame = 'fk4'
        else:
            frame = 'fk5'
    
    position = SkyCoord(data["RA"], data["Dec"], unit=(u.hourangle, u.degree), equinox=equinox, frame=frame)
    
    results = dict(
        Name = data['Name'].strip(),
        Position = position,
    )
    for keywordvalue in data.get("Keywords","").split():
        if keywordvalue.count("=") < 1:
            warnings.warn("Illegal Keyword Argument: '{}'".format(keywordvalue))
            continue
        keyword, value = keywordvalue.split("=",1)
        keyword = keyword.strip()
        if keyword in set(["Name", "Position"]):
            warnings.warn("Illegal Keyword Name: '{}'".format(keyword))
        results[keyword] = value.strip()
    return results
    
def read_skip_comments(filename, comments="#"):
    """Read a filename, yielding lines that don't start with comments."""
    with open(filename, 'r') as stream:
        for line in stream:
            if not line.startswith(comments):
                yield line.strip().strip("\n\r")
    
def parse_starlist(starlist):
    """Parse a starlist into a sequence of dictionaries."""
    for line in read_skip_comments(starlist):
        yield parse_starlist_line(line)
    



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
                    starlist.write("{name:<15s} {ra:s} {dec:s} {epoch:.0f} {keywords:s}".format(
                        name = name.strip(),
                        ra = loc.ra.format(u.hour, sep=" ", pad=True),
                        dec = loc.dec.format(sep=" ", alwayssign=True),
                        epoch = loc.equinox.jyear,
                        keywords = " ".join(comments),
                    ))
                    starlist.write("\n")
                else:
                    self.log.warning("Region {!r} not parsed. It is not a circle.".format(region))
                    
        

        

        