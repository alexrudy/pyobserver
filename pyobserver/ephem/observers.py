# -*- coding: utf-8 -*-
# 
#  observers.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-03.
#  Copyright 2014 Alexander Rudy. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

import ephem

import six
import datetime
import pytz
import astropy.units as u
from astropy.coordinates import ICRS, FK5, AltAz, Angle
from astropy.time import Time

from pyshell.config import StructuredConfiguration
from pyshell.yaml import PyshellLoader, PyshellDumper
from pyshell.astron.yaml_tools import astropy_quantity_yaml_factory

from .bases import EphemClass, EphemAttribute, EphemCelciusAttribute

astropy_quantity_yaml_factory(Angle, PyshellLoader, PyshellDumper, six.text_type)
astropy_quantity_yaml_factory(u.Quantity, PyshellLoader, PyshellDumper)

class Observer(EphemClass):
    """Make an observer."""
    
    __wrapped_class__ = ephem.Observer
    
    def __init__(self, **kwargs):
        super(Observer, self).__init__()
        for keyword, value in kwargs.items():
            setattr(self, keyword, value)
            
    def __repr__(self):
        """Represent an observer."""
        repr_str = "<{0}".format(self.__class__.__name__)
        if hasattr(self, 'name'):
            repr_str += " '{0}'".format(self.name)
        if hasattr(self, 'lat') and hasattr(self, 'lon'):
            repr_str += " at ({0},{1})".format(self.lat.to_string(u.degree, sep=":", alwayssign=True), self.lon.to_string(u.degree, sep=":", alwayssign=True))
        if hasattr(self, '_timezone'):
            repr_str += " ({0})".format(self.timezone)
        return repr_str + ">"
    
    @property
    def timezone(self):
        """The timezone for this observer."""
        return self._timezone
        
    @timezone.setter
    def timezone(self, value):
        """Set the local timezone."""
        if isinstance(value, six.string_types):
            value = pytz.timezone(value)
        elif not isinstance(value, datetime.tzinfo):
            raise TypeError("Timezone must be an instance of {}".format(datetime.tzinfo))
        self._timezone = value
    
    elevation = EphemAttribute("elevation", u.m)
    
    temp = EphemCelciusAttribute("temp")
    
    pressure = EphemAttribute("pressure", 1e-3 * u.bar)
    

_observatories_data = StructuredConfiguration.fromresource('pyobserver', 'data/observatories.yml')
def get_observatory(key):
    """Get an observatory object from the database."""
    return Observer(**_observatories_data[key])