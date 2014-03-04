# -*- coding: utf-8 -*-
# 
#  visibility.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-03.
#  Copyright 2014 Alexander Rudy. All rights reserved.
# 


from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

import numpy as np

import astropy.units as u

from .targets import Sun, Moon



class Night(object):
    """An object to represent an observing night."""
    
    _sun = Sun()
    _moon = Moon()
    
    def __init__(self, observer, date):
        super(Night, self).__init__()
        self.observer = observer
        self.date = date
        
    @property
    def start(self):
        """Start"""
        self.observer.date = self.date
        return self.observer.next_setting(self.sun)
        
    @property
    def end(self):
        """End"""
        self.observer.date = self.start
        return self.observer.next_rising(self.sun)
        
    @property
    def length(self):
        """Night length."""
        return self.end - self.start
        
    @property
    def sun(self):
        """The state of the sun on this night."""
        self._sun.compute(self.observer)
        return self._sun
        
    @property
    def moon(self):
        """The state of the sun on this night."""
        self._moon.compute(self.observer)
        return self._moon
        
    def iterate(self, increment):
        """Iterate through a night at a given increment, from sunset to sunrise."""
        time = self.start
        while time <= self.end:
            yield time
            time = time + increment
            
    def increments(self, increment):
        """The number of increments which will occur in this night."""
        return (self.length/increment) + 1

class VisibilityPlot(object):
    """A single observing night at a specific observatory."""
    
    increment = 6 * u.minute
    
    def __init__(self, observer, date):
        super(VisibilityPlot, self).__init__()
        self.night = Night(observer, date)
        self.targets = set()
    
    def __call__(self, ax):
        """Make a visibility plot on a given axes object."""
        if hasattr(ax, '_twinx_ax'):
            ax_z = ax._twinx_ax
        else:
            ax_z = ax.twinx()
            ax._twinx_ax = ax_z
        
        n = self.night.increments(self.increment)
        times = list(self.night.iterate(self.increment))
        dt = [ time.datetime for time in times ]
        for target in self.targets:
            zenith_angle = np.zeros((n,), dtype=float) * u.degree
            moon_distance = np.zeros((n,), dtype=float) * u.degree
            for i,time in enumerate(times):
                self.night.observer.date = time
                target.compute(self.night.observer)
                zenith_angle[i] = target.alt
                moon_distance[i] = self.night.moon.position.separation(target.position)
            ax.plot(dt, zenith_angle, '-', label=target.name)
        ax.legend()
        