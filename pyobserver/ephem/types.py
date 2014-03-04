# -*- coding: utf-8 -*-
# 
#  types.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-03.
#  Copyright 2014 University of California. All rights reserved.
# 

"""
Conversion functions for Astropy/PyEphem types.
"""

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

import astropy.time
import astropy.coordinates
import astropy.units as u
import ephem

import functools
import six
import inspect
import abc

from pyshell.util import descriptor__get__

__all__ = ['register_transformation', 'convert', 'convert_astropy_to_ephem', 'convert_ephem_to_astropy']

_astropy_transformations = {}
_ephem_transformations = {}
_transform_pairs = set()

def register_transformation(astropy_class, ephem_class, ephem_to_astropy, astropy_to_ephem):
    """Register a transformation between :mod:`astropy` and :mod:`ephem` ."""
    if ephem_to_astropy is not None:
        if astropy_class in _astropy_transformations:
            warnings.warn("This will overwrite the astropy transformation for {}".format(astropy_class))
        _astropy_transformations[ephem_class] = ephem_to_astropy
        _transform_pairs.add((ephem_class, astropy_class))
    if astropy_to_ephem is not None:
        if ephem_class in _ephem_transformations:
            warnings.warn("This will overwrite the ephem transformation for {}".format(ephem_class))
        _ephem_transformations[astropy_class] = astropy_to_ephem
        _transform_pairs.add((astropy_class, ephem_class))
    
def _check_transformation(obj, result):
    """Check a transformation is valid."""
    if (type(obj), type(result)) not in _transform_pairs:
        warnings.warn("Types shouldn't have converted: {} -> {}".format(type(obj), type(result)))
    return result
    
def convert_astropy_to_ephem(obj):
    """Convert an object from its :mod:`astropy` representation to its :mod:`ephem`  representation"""
    if type(obj) not in _ephem_transformations:
        raise TypeError("Can't convert type {}".format(type(obj)))
    return _check_transformation(obj, _ephem_transformations[type(obj)](obj))
    
def convert_ephem_to_astropy(obj):
    """Convert an object from its :mod:`ephem`  representation to its :mod:`astropy` representation"""
    if type(obj) not in _astropy_transformations:
        raise TypeError("Can't convert type {}".format(type(obj)))
    return _check_transformation(obj, _astropy_transformations[type(obj)](obj))
    
def convert_ephem_to_astropy_weak(obj):
    """Convert ephem to astropy if necessary."""
    obj_type = astropy_or_ephem(obj)
    if obj_type == "ephem":
        return convert_ephem_to_astropy(obj)
    else:
        return obj
        
def convert_astropy_to_ephem_weak(obj):
    """Convert astropy to ephem, if necessary."""
    obj_type = astropy_or_ephem(obj)
    if obj_type == "astropy":
        return convert_astropy_to_ephem(obj)
    elif isinstance(obj, AttributeConverter):
        return obj.__wrapped_instance__
    elif inspect.isclass(obj) and issubclass(obj, AttributeConverter):
        return obj.__wrapped_class__
    else:
        return obj
    
def convert(obj):
    """Convert the object"""
    if type(obj) in _astropy_transformations:
        return convert_ephem_to_astropy(obj)
    elif type(obj) in _ephem_transformations:
        return convert_astropy_to_ephem(obj)
    else:
        raise TypeError("Can't convert type {}".format(type(obj)))
    
def astropy_or_ephem(obj):
    """Return whether an object is in astropy, ephem, or none."""
    if type(obj) in _astropy_transformations:
        return "ephem"
    elif type(obj) in _ephem_transformations:
        return "astropy"
    else:
        return "neither"

# DATE OBJECTS

def ea_date(ephem_date):
    """Convert an :mod:`ephem` date to an :mod:`astropy` time object, via :mod:`datetime`"""
    return astropy.time.Time(ephem_date.datetime(), scale='utc')
    
def ae_date(astropy_time):
    """Convert an :mod:`astropy` time to an :mod:`ephem`  date object, via :mod:`datetime`"""
    return ephem.Date(astropy_time.datetime)
    
register_transformation(astropy.time.Time, ephem.Date, ea_date, ae_date)

# ANGLE Objects

def _ea_angle_method(astropy_angle_class):
    """Astropy Angle Class"""
    def ea_angle(ephem_angle):
        """Convert an :mod:`ephem` angle to an :mod:`astropy` angle."""
        return astropy_angle_class(float(ephem_angle), unit=u.radian)
    return ea_angle
    
def ae_angle(astropy_angle):
    """Convert an :mod:`astropy` angle to an :mod:`ephem` angle."""
    return ephem.degrees(astropy_angle.to(u.radian).value)
    
def _angle_tuples(astropy_angle_class, reverse=True):
    """Return an angle class tuple"""
    if reverse:
        return (astropy_angle_class, ephem.Angle, _ea_angle_method(astropy_angle_class), ae_angle)
    else:
        return (astropy_angle_class, ephem.Angle, None, ae_angle)
    
register_transformation(*_angle_tuples(astropy.coordinates.Latitude, reverse=False))
register_transformation(*_angle_tuples(astropy.coordinates.Longitude, reverse=False))
register_transformation(*_angle_tuples(astropy.coordinates.Angle))
# Mixin Class

@six.add_metaclass(abc.ABCMeta)
class AttributeConverter(object):
    """Converts attributes"""
    
    __wrapped_class__ = None
    
    def __init__(self, *args, **kwargs):
        """Initialize this instance."""
        super(AttributeConverter, self).__init__(*args, **kwargs)
        self.__dict__['__wrapped_instance__'] = self.__wrapped_class__(*args, **kwargs)
    
    @staticmethod
    def decorate_attribute_convert(f):
        """Convert function results from """
        @functools.wraps(f)
        def wrap_convert(*args, **kwargs):
            e_args = [convert_astropy_to_ephem_weak(arg) for arg in args]
            e_kwargs = { key:convert_astropy_to_ephem_weak(kwargs[key]) for key in kwargs }
            return convert_ephem_to_astropy_weak(f(*e_args, **e_kwargs))
        return wrap_convert
        
    def __getattr__(self, attribute_name):
        """Manipulate attribute access to use :mod:`astropy` objects."""
        attribute = getattr(self.__wrapped_instance__, attribute_name)
        if six.callable(attribute) and isinstance(attribute.__self__, self.__wrapped_class__):
            return self.decorate_attribute_convert(attribute)
        return convert_ephem_to_astropy_weak(attribute)
        
    def __setattr__(self, attribute_name, value):
        """Set attributes, with type conversion."""
        if (not attribute_name.startswith("__")) and hasattr(self.__wrapped_instance__, attribute_name):
            value = convert_astropy_to_ephem_weak(value)
            return setattr(self.__wrapped_instance__, attribute_name, value)
        return super(AttributeConverter, self).__setattr__(attribute_name, value)
    
    @classmethod
    def __subclasshook__(cls, C):
        if cls.__wrapped_class__ is not None:
            if issubclass(C, cls.__wrapped_class__):
                return True
        return NotImplemented

class WrappedUnitAttribute(object):
    """A descriptor which wraps an ephem attribute, giving it astropy units.."""
    def __init__(self, name, unit):
        super(WrappedUnitAttribute, self).__init__()
        self.name = name
        self.unit = unit
        
    def __set__(self, obj, value):
        """Set named the attribute"""
        setattr(obj.__wrapped_instance__, self.name, u.Quantity(value, self.unit).value)
        
    @descriptor__get__
    def __get__(self, obj, objtype):
        """Get the named attribute."""
        return u.Quantity(getattr(obj.__wrapped_instance__, self.name), self.unit)
        
_CELCIUS_OFFSET = 273.15 * u.K
        
class CelciusAttribute(WrappedUnitAttribute):
    """A unit attribute in Celcius"""
    def __init__(self, name):
        super(CelciusAttribute, self).__init__(name, unit=u.K)
        
    def __set__(self, obj, value):
        """Set with offset."""
        return super(CelciusAttribute, self).__set__(obj, value - _CELCIUS_OFFSET)
        
    @descriptor__get__
    def __get__(self, obj, objtype):
        """Get with offsets."""
        return super(CelciusAttribute, self).__get__(obj, objtype) + _CELCIUS_OFFSET
        
    
        
        