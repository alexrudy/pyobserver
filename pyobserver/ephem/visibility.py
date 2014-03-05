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
import pytz
import astropy.units as u
import astropy.time
import astropy.table
import pandas as pd
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
        
    @staticmethod
    def extract_value(attr_value, attr_unit):
        """Extract value in unit"""
        return attr_value
        
    def collect(self, target, increment, attrs, timecol='Time'):
        """Collect a list of attributes across a target over a night."""
        times = self.times(increment)
        result = {}
        self.observer.date = self.start
        target.compute(self.observer)
        for attr in attrs:
            attr_value = getattr(target, attr)
            result[attr] = np.zeros((len(times),), dtype=attr_value.dtype) * attr_value.unit
        
        for i, time in enumerate(times):
            self.observer.date = time
            target.compute(self.observer)
            for attr in attrs:
                result[attr][i] = getattr(target, attr)
        result[timecol] = [ time.datetime for time in times ]
        return pd.DataFrame(result)

    

def airmass(altitude):
    """Compute airmass from altitude."""
    zenith_angle = 90 * u.degree - altitude
    airmass = 1.0 / np.cos(zenith_angle)
    return airmass

class VisibilityPlot(object):
    """A single observing night at a specific observatory."""
    
    increment = 1 * u.minute
    
    def __init__(self, observer, date):
        super(VisibilityPlot, self).__init__()
        self.night = Night(observer, date)
        self.targets = set()
    
    def __call__(self, ax, el=(1.0 * u.degree, 90 * u.degree), unit=u.degree, moon_distance_spacing=(60 * u.minute), moon_distance_maximum=(30 * u.degree)):
        """Make a visibility plot on a given axes object."""
        import matplotlib.dates
        import matplotlib.ticker
        utc_tz = pytz.timezone("UTC")
        date_locator = matplotlib.dates.AutoDateLocator()
        date_formatter = matplotlib.dates.AutoDateFormatter(date_locator, tz=utc_tz)
        local_tz = pytz.timezone("US/Hawaii")
        local_date_locator = matplotlib.dates.AutoDateLocator()
        local_date_formatter = matplotlib.dates.AutoDateFormatter(local_date_locator, tz=local_tz)
        airmass_formatter = matplotlib.ticker.FuncFormatter(lambda x,p: "{0.value:.2f} {0.unit:latex}".format(airmass(x * u.degree)))
        unit_formatter = matplotlib.ticker.FuncFormatter(lambda x,p: "{0.value} {0.unit:latex}".format(x * unit))
        ylim_values = (el[0].to(unit).value, el[1].to(unit).value)
        
        ax_z = ax._make_twin_axes()
        ax_z.xaxis.tick_top()
        ax_z.xaxis.set_label_position('top')
        ax.xaxis.tick_bottom()
        ax_z.yaxis.tick_right()
        ax_z.yaxis.set_label_position('right')
        ax_z.yaxis.set_offset_position('right')
        ax.yaxis.tick_left()
        ax_z.patch.set_visible(False)
        
        times = self.night.times(self.increment)
        for target in self.targets:
            altitude_angle = np.zeros((len(times),), dtype=float) * u.degree
            moon_distance = np.zeros((len(times),), dtype=float) * u.degree
            last_moon_distance = self.night.start
            for i,time in enumerate(times):
                self.night.observer.date = time
                target.compute(self.night.observer)
                altitude_angle[i] = target.alt
                moon_distance[i] = self.night.moon.position.separation(target.position)
                if last_moon_distance + moon_distance_spacing <= time and (altitude_angle[i] >= el[0] and moon_distance[i] <= moon_distance_maximum):
                    ax.annotate(
                        s = "{0.value:0.0f} {0.unit:latex}".format(moon_distance[i]),
                        xy = (time.datetime, altitude_angle[i].to(unit).value),
                        xytext = [0.0, -40.0],
                        textcoords='offset points',)
                    last_moon_distance = time
                
                
            ax.plot(times.datetime, altitude_angle.to(unit).value, '-', label=target.name)
            ax_z.plot(times.datetime, altitude_angle.to(unit).value, ':')
        
        ax.axvline(self.night.start.datetime)
        
        ax.xaxis.set_major_locator(date_locator)
        ax.xaxis.set_major_formatter(date_formatter)
        ax.yaxis.set_major_formatter(unit_formatter)
        ax.set_ylabel("Elevation ({0:latex})".format(u.degree))
        ax.set_xlabel("Time ({0!s})".format(utc_tz))
        ax.grid(True, axis='both')
        ax.xaxis.tick_bottom()
        
        ax_z.yaxis.set_major_formatter(airmass_formatter)
        ax_z.set_ylabel(r"Airmass ($\sec(z)$)")
        ax_z.set_xlabel("Time ({0!s})".format(local_tz))
        ax_z.xaxis.tick_top()
        ax_z.xaxis.set_major_locator(local_date_locator)
        ax_z.xaxis.set_major_formatter(local_date_formatter)
        ax_z.xaxis.set_visible(True)
        ax_z.xaxis.set_label_position('top')
        
        ax.set_ylim(*ylim_values)
        ax_z.set_ylim(*ylim_values)
        ax_z.set_xlim(*ax.get_xlim())
        ax.legend()
        