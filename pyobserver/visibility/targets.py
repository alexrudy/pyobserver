# -*- coding: utf-8 -*-
# 
#  targets.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-23.
#  Copyright 2014 Alexander Rudy. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division, print_function)


from astropyephem import FixedBody
from astropy.coordinates import SkyCoord, AltAz, FK5, FK4
from ..starlist import parse_starlist_line, read_skip_comments

class StarlistBase(object):
    """Base class for starlist."""
    
    REGISTRY = {}
    
    def __init__(self, *args, **kwargs):
        super(StarlistBase, self).__init__()
    
    @classmethod
    def from_starlist(cls, text):
        """Produce a fixed-body item from a starlist."""
        data = parse_starlist_line(text)
        for key in data:
            data[key.lower()] = data.pop(key)
        obj = None
        klass = cls.REGISTRY[type(data['position'].frame)]
        return klass(**data)
    
    @classmethod
    def register(cls, coords):
        """Register a superclass to this constructor."""
        def _register(klass):
            cls.REGISTRY[coords] = klass
            return klass
        return _register

@StarlistBase.register(AltAz)
class AltAzTarget(StarlistBase):
    """Altitude and azimuthal target."""
    
    def __init__(self, name, **kwargs):
        super(AltAzTarget, self).__init__()
        self.name = name
        for key in kwargs:
            setattr(self, key, kwargs[key])
    
    def position_string(self):
        """Return a string representation of the position"""
        return "Alt={alt},Az={az}".format(
            alt = self.position.alt,
            az = self.position.az,
        )
    
    def __repr__(self):
        """Represent this object"""
        repr_str = "<{} ".format(self.__class__.__name__)
        if self.name is not None:
            repr_str += "'{}'".format(self.name)
        try:
            repr_str += " at ({})".format(self.position_string()

            )
        except:
            pass
        return repr_str + ">"
    
    @property
    def fixed_position(self):
        """The position using :class:`astropy.coordinates.ICRS` in astrometric coordinates."""
        return NotImplementedError("Can't be at a fixed position in AltAz")
        
    @property
    def position(self):
        """The position of this source in AltAz coordinates.."""
        return self._position
        
    @position.setter
    def position(self, value):
        """Set the position attribute with an AltAz coordinate."""
        self._position = AltAz(value)
    
@StarlistBase.register(FK4)
@StarlistBase.register(FK5)
class Target(FixedBody, StarlistBase):
    """A subclass of FixedBody with a starlist interface."""
    pass
    
def parse_starlist_targets(starlist):
    """Parse a starlist into targets."""
    for line in read_skip_comments(starlist):
        yield Target.from_starlist(line)