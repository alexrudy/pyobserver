# -*- coding: utf-8 -*-
# 
#  targets.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-03.
#  Copyright 2014 Alexander Rudy. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)


import ephem

import astropy.units as u
from astropy.coordinates import ICRS, FK5, AltAz
from astropy.time import Time

from .types import convert, ComputeConverter, WrappedUnitAttribute

EQUINOX_J2000 = Time('J2000', scale='utc')

class HasPosition(ComputeConverter):
    """A target object, subclassed from ephem, which uses astropy coordinates."""
    
    def __repr__(self):
        """Represent this object"""
        repr_str = "<{} ".format(self.__class__.__name__)
        if self.name is not None:
            repr_str += "'{}'".format(self.name)
        try:
            repr_str += " at (RA={ra},DEC={dec})".format(
                ra = self.position.ra.format(u.hour, sep=":", pad=True),
                dec = self.position.dec.format(sep=":", alwayssign=True),
            )
        except:
            repr_str += " at {}".format(id(self))
        return repr_str + ">"
    
    @property
    def _equinox(self):
        """The equinox of this Body"""
        return self._epoch
        
    @property
    def altaz(self):
        """Return the Alt/Az coordinate for this position."""
        return AltAz(self.az, self.alt)
        
    @property
    def position(self):
        """Return the astrometric computed position."""
        return self.astrometric_position
    
    @property
    def astrometric_position(self):
        """Return the astrometric computed position."""
        return FK5(self.a_ra, self.a_dec, equinox=self._equinox).transform_to(ICRS)
    
    @property
    def geocentric_position(self):
        """Return the geocentric computed position."""
        return FK5(self.g_ra, self.g_dec, equinox=self._equinox).transform_to(ICRS)
        
    @property
    def apparent_position(self):
        """Return the apparent computed position."""
        return FK5(self.ra, self.dec, equinox=self._equinox).transform_to(ICRS)
        
        

class Target(HasPosition, ephem.FixedBody):
    """A Target is an object with a fixed RA and DEC"""
    
    def __init__(self, position = None, name = None):
        super(Target, self).__init__()
        if position is not None:
            self.fixed_position = position
        if name is not None:
            self.name = name
    
    def __repr__(self):
        """Represent this object"""
        repr_str = "<{} ".format(self.__class__.__name__)
        if self.name is not None:
            repr_str += "'{}'".format(self.name)
        repr_str += " at (RA={ra},DEC={dec})".format(
            ra = self.fixed_position.ra.format(u.hour, sep=":", pad=True),
            dec = self.fixed_position.dec.format(sep=":", alwayssign=True),
        )
        return repr_str + ">"
    
    @property
    def fixed_position(self):
        """The position using :class:`astropy.coordinates.ICRS` in astrometric coordinates."""
        return FK5(self._ra, self._dec, equinox=self._equinox).transform_to(ICRS)
        
    @fixed_position.setter
    def fixed_position(self, coord):
        """Set the position using :class:`astropy.coordinates.ICRS`."""
        coord_fk5 = coord.transform_to(FK5)
        self._ra = coord_fk5.ra
        self._dec = coord_fk5.dec
        self._epoch = coord_fk5.equinox
        
    def to_starlist(self):
        """To a starlist format"""
        string = "{name:<20s} {ra:s} {dec:s} {epoch:.0f}".format(
                                name = self.name.strip(),
                                ra = self.position.ra.format(u.hour, sep=" ", pad=True),
                                dec = self.position.dec.format(sep=" ", alwayssign=True),
                                epoch = self.position.equinox.jyear,
                            )
        return string
        
    

class Sun(HasPosition, ephem.Sun):
    """Our star."""
    pass
    
class Moon(HasPosition, ephem.Moon):
    """Earth's Moon"""
    pass
        
        