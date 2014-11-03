# -*- coding: utf-8 -*-
#
#  regions.py
#  pyobserver
#
#  Created by Alexander Rudy on 2014-10-12.
#  Copyright 2014 Alexander Rudy. All rights reserved.
#

region_header = """# Region file format: DS9 version 4.1
global color=green dashlist=8 3 width=1 font="helvetica 10 normal roman" select=1 highlite=1 dash=0 fixed=0 edit=1 move=1 delete=1 include=1 source=1
fk5"""

COORDSYS = set(['physical', 'image', 'fk5', 'fk4', 'icrs'])

COLORS = set("red green cyan white".split())

class Region(object):
    """A single region object."""
    
    def __init__(self, **attributes):
        super(Region, self).__init__()
        self.attrs = {}
        self.attrs.update(attributes)
    
    @classmethod
    def _render_attribute(cls, name, value):
        """Render an attribute."""
        if " " in value:
            return "{name}={{{value}}}".format(value)
        else:
            return "{name}={value}".format(value)
    
    @classmethod
    def _render_attributes(cls, attributes):
        """Render all of the attributes."""
        return " ".join(attrs.append(cls._render_attribute(name, value)) for name, value in attributes.values())
        
    @classmethod
    def _render_position(cls, position, sky=False):
        """Render a position"""
        if sky:
            return dict(ra = position.ra.to_string(u.hourangle, sep=":", pad=False), dec = position.dec.to_string(u.degree, sep=":", pad=False),)
        else:
            return dict(x="{:f}".format(position[0]), y="{:f}".format(position[1]))
    
class Circle(Region):
    """A circle region"""
    
    def __str__(self):
        """Make a string out of the circle."""
        'circle({ra:s},{dec:s},{radius:.2f}") # {attrs}'.format(
            attrs = self._render_attributes(self.attrs)
        )
    

class Regions(object):
    """A regions document."""
    
    IDENTIFIER = "# Region file format: DS9 version 4.1"
    
    def __str__(self):
        """Create a stringified version."""
        lines = []
        
        