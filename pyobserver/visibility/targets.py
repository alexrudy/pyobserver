# -*- coding: utf-8 -*-
# 
#  targets.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-23.
#  Copyright 2014 Alexander Rudy. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division, print_function)

import collections
import numpy as np
import os, os.path
import six

import astropy.units as u
from astropy.coordinates import SkyCoord, AltAz, FK5, FK4

from astropyephem import FixedBody

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
        self._position = SkyCoord(value, frame=AltAz)
    
@StarlistBase.register(FK4)
@StarlistBase.register(FK5)
class Target(FixedBody, StarlistBase):
    """A subclass of FixedBody with a starlist interface."""
    
    def to_starlist(self):
        """Return a starlist line from this target"""
        pos = self.fixed_position.transform_to(FK5)
        name = self.name.replace(" ","_")
        keywords = " ".join("{}={}".format(attr, six.text_type(getattr(self, attr))) for attr in self.__keywords__ if not attr.startswith("_"))
        return "{name:<15s} {ra:s} {dec:s} {epoch:.0f} {keywords:s}".format(
                                name = name.strip(),
                                ra = pos.ra.to_string(u.hour, sep=" ", pad=True),
                                dec = pos.dec.to_string(u.deg, sep=" ", alwayssign=True),
                                epoch = pos.equinox.jyear,
                                keywords = keywords)
    
class Starlist(list):
    """A set of target objects."""
    
    TYPE = Target
    
    @classmethod
    def from_starlist(cls, filename):
        """Produce this starlist from a"""
        return cls(cls.TYPE.from_starlist(line) for line in read_skip_comments(filename))
        
    def to_starlist(self, filename):
        """docstring for to_starlist"""
        with open(filename, 'w') as stream:
            stream.write("# Starlist: {}".format(os.path.basename(filename)))
            stream.write("\n")
            for target in self:
                stream.write(target.to_starlist())
                stream.write("\n")
    
    def add(self, value):
        """Alias set-like add to append."""
        if value not in self:
            self.append(value)
    
    def catalog(self):
        """Return a unified catalog array from the targets."""
        ras =  np.array([ target.fixed_position.ra.value for target in self ]) * self[0].fixed_position.ra.unit
        decs = np.array([ target.fixed_position.dec.value for target in self ]) * self[0].fixed_position.dec.unit
        return SkyCoord(ras, decs, frame='icrs')
    
    def __setitem__(self, key, value):
        """Ensure that targets aren't added twice."""
        if not isinstance(value, self.TYPE):
            raise TypeError("Starlist items must inherit from {!r}. Got {!r}".format(self.TYPE, type(value)))
        if value in self:
            raise ValueError("Can't add target {!r} to starlist twice!".format(value))
        super(Starlist, self).__setitem__(key, value)
        
    def get_guidestars(self, target, sep=(2 * u.arcmin)):
        """Get any guidestars for a given target."""
        catalog = self.catalog()
        matches, sep2d, distances = target.fixed_position.match_to_catalog_sky(catalog, nthneighbor=2)
        return set(self[i] for i in np.atleast_1d(matches)[sep2d <= sep])
        
    def map_guidestars(self, sep=(2 * u.arcmin)):
        """Create a dictionary mapping targets to guidestars."""
        targets = {}
        for target in self:
            if target not in targets:
                # Trying a new target.
                found_target = False
                
                for other_target in targets:
                    
                    # Only act if we are close to the other target.
                    if other_target.fixed_position.separation(target.fixed_position) <= sep:
                        found_target = True
                        if hasattr(other_target, 'lgs'):
                            targets[other_target].add(target)
                            continue
                        if hasattr(target, 'lgs'):
                            targets[target] = targets.pop(other_target)
                            continue
                        if hasattr(other_target, 'rmag'):
                            targets[target] = targets.pop(other_target)
                            continue
                        if hasattr(target, 'rmag'):
                            targets[other_target].add(target)
                            continue
                        warnings.warn("Two close targets found: {} and {}, can't differentiatie between them. Using first one: {}".format(
                            other_target.name, target.name, other_target.name
                        ))
                if not found_target:
                    targets[target] = set()
        return targets
        
    def filter_guidestars(self, sep=(2 * u.arcmin)):
        """Filter out guidestars from this starlist."""
        target_map = self.map_guidestars(sep=sep)
        return Starlist(target_map.keys())
    
    

def parse_starlist_targets(starlist):
    """Parse a starlist into targets."""
    for line in read_skip_comments(starlist):
        yield Target.from_starlist(line)