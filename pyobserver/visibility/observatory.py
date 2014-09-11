# -*- coding: utf-8 -*-
# 
#  observatory.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-23.
#  Copyright 2014 Alexander Rudy. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division, print_function)


from astropyephem import Observer

import six
import pytz
import datetime

import astropy.units as u
from astropy.coordinates import SkyCoord, ICRS, FK5, AltAz, Angle
from astropy.time import Time

from pyshell.config import StructuredConfiguration
from pyshell.yaml import PyshellLoader, PyshellDumper
from pyshell.astron.yaml_tools import astropy_quantity_yaml_factory, astropy_direct_yaml_factory

astropy_direct_yaml_factory(Angle, PyshellLoader, PyshellDumper)
astropy_quantity_yaml_factory(u.Quantity, PyshellLoader, PyshellDumper)

_observatories_data = StructuredConfiguration.fromresource('pyobserver', 'data/observatories.yml')
def get_observatory(key):
    """Get an observatory object from the database."""
    o = Observatory(**_observatories_data[key])
    if not hasattr(o, 'name'):
        o.name = key
    return o

class Observatory(Observer):
    """Observatory is a fancy observer with a few extra properties."""
    
    def __repr__(self):
        """Represent an observer."""
        repr_str = "<{0}".format(self.__class__.__name__)
        if hasattr(self, 'name'):
            repr_str += " '{0}'".format(self.name)
        if hasattr(self, 'lat') and hasattr(self, 'lon'):
            repr_str += " at ({0},{1})".format(self.lat.to_string(u.degree, sep=":", alwayssign=True), self.lon.to_string(u.degree, sep=":", pad=True))
        if hasattr(self, 'date'):
            repr_str += " {0.datetime:%Y-%m-%d %H:%M:%S}".format(self.date)
        if hasattr(self, '_timezone'):
            repr_str += " ({})".format(self.timezone.zone)
        return repr_str + ">"
        
    
    @property
    def timezone(self):
        """Return the tz_info object."""
        return self._timezone
        
    @timezone.setter
    def timezone(self, value):
        """Set the tz_info object."""
        if isinstance(value, six.string_types):
            self._timezone = pytz.timezone(value)
        elif isinstance(value, datetime.tz_info):
            self._timezone = value
        else:
            raise ValueError("{}.timezone must be an instance of {} or a string which represents a timezone to {}".format(self.__class__.__name__, datetime.tz_info, pytz.__name__))
    
    @classmethod
    def from_name(cls, name):
        """Load an observatory by name."""
        return get_observatory(name)
    