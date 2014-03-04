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
import astropy.time

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
        
    def times(self, increment):
        """Iterate through a night at a given increment, from sunset to sunrise."""
        data = []
        for i in range(int((self.length.to(u.day)/increment).to(1)) + 1):
            data.append(self.start + increment * i)
        return astropy.time.Time([ d.datetime for d in data ], scale='utc')
    

class VisibilityPlot(object):
    """A single observing night at a specific observatory."""
    
    increment = 1 * u.minute
    
    def __init__(self, observer, date):
        super(VisibilityPlot, self).__init__()
        self.night = Night(observer, date)
        self.targets = set()
    
    def __call__(self, ax):
        """Make a visibility plot on a given axes object."""
        import matplotlib.dates
        locator = matplotlib.dates.AutoDateLocator()
        formatter = matplotlib.dates.AutoDateFormatter(locator)
        
        times = self.night.times(self.increment)
        for target in self.targets:
            altitude_angle = np.zeros((len(times),), dtype=float) * u.degree
            moon_distance = np.zeros((len(times),), dtype=float) * u.degree
            for i,time in enumerate(times):
                self.night.observer.date = time
                target.compute(self.night.observer)
                altitude_angle[i] = target.alt
                moon_distance[i] = self.night.moon.position.separation(target.position)
            ax.plot(times.plot_date, altitude_angle, '-', label=target.name)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        ax.set_ylim(0, 90)
        ax.legend()
        