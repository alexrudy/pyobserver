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
import datetime
import astropy.units as u
import astropy.time
import astropy.table
from astropy.utils.console import ProgressBar
import pandas as pd
from astropyephem.targets import Sun, Moon
import sys
import warnings

class Night(object):
    """An object to represent an observing night."""
    
    _sun = Sun()
    _moon = Moon()
    
    def __init__(self, observer, date):
        super(Night, self).__init__()
        self.observer = observer
        self.date = date
        
    def __repr__(self):
        repr_str = "<{}".format(self.__class__.__name__)
        if hasattr(self, '_date'):
            repr_str += " @{0:%Y-%m-%d}".format(self.date.datetime)
            repr_str += " for {0.value:.1f} {0.unit}".format(self.length.to(u.hour))
        return repr_str + ">"
        
    @property
    def date(self):
        """Date"""
        return self._date
        
    @date.setter
    def date(self, value):
        """Set the date, night start and night end."""
        self._date = value
        self.observer.date = value
        self.end = self.observer.next_rising(self.sun)
        self.observer.date = self.end
        self.start = self.observer.previous_setting(self.sun)
        
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
            result[attr] = np.zeros((len(times),), dtype=np.dtype(type(attr_value))) * getattr(attr_value, 'unit', 0)
        
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
    
def setup_dual_axis(ax1):
    """Set up an axis for dual-scales.
    
    Dual scales are those where the left and right y-axes refer to the same
    data, and the top and bottom x-axes refer to the same data. The plot
    then shows two related scales.
    
    This method uses the private :meth:`~matplotlib.axes.Axes._make_twin_axes` command, then changes
    thea axis behaviors using normal matplotlib commands.
    
    """
    ax2 = ax1._make_twin_axes()
    
    # New X-Axis
    ax2.xaxis.tick_top()
    ax2.xaxis.set_label_position('top')
    
    # New Y-Axis
    ax2.yaxis.tick_right()
    ax2.yaxis.set_label_position('right')
    ax2.yaxis.set_offset_position('right')
    
    # Hide the patch
    ax2.patch.set_visible(False)
    
    # Tick only where necessary on the old axis.
    ax1.xaxis.tick_bottom()
    ax1.yaxis.tick_left()
    
    return (ax1, ax2)

class EphemerisPlotBase(object):
    """Base class for Ephemeris Plotting"""
    
    def setup_dual_axis(self, ax):
        """Setup a dual axis for use with the airmass chart."""
        ax, ax2 = setup_dual_axis(ax)
        return ax2
    
    @staticmethod
    def format_timezone_axis(axis, timezone, label="Time", fmt=None):
        """Set up an axis with formatters for a specific timezone."""
        import matplotlib.dates
        if not isinstance(timezone, datetime.tzinfo):
            timezone = pytz.timezone(timezone)
        date_locator = matplotlib.dates.AutoDateLocator()
        if fmt is None:
            date_formatter = matplotlib.dates.AutoDateFormatter(date_locator, tz=timezone)
        else:
            date_formatter = matplotlib.dates.DateFormatter(fmt, tz=timezone)
        axis.set_major_locator(date_locator)
        axis.set_major_formatter(date_formatter)
        if label:
            axis.set_label_text("{0:s} ({1:s})".format(label, timezone))
        
    @staticmethod
    def format_units_axis(axis, unit, label=""):
        """Set an axis to have unit formatting."""
        import matplotlib.ticker
        unit_formatter = matplotlib.ticker.FuncFormatter(lambda x,p: "{0.value} {0.unit:latex}".format(x * unit))
        axis.set_major_formatter(unit_formatter)
        if label:
            axis.set_label_text("{0:s} ({1:latex})".format(label, unit))
        
    @staticmethod
    def format_airmass_axis(axis, unit, label=r"Airmass ($\sec(z)$)"):
        """Format an axis in airmass."""
        import matplotlib.ticker
        airmass_formatter = matplotlib.ticker.FuncFormatter(lambda x,p: "{0.value:.2f}".format(airmass(x * u.degree)))
        axis.set_major_formatter(airmass_formatter)
        if label:
            axis.set_label_text(label)


class ObservabilityPlot(EphemerisPlotBase):
    """A plot of observability throughout a Semester."""
    def __init__(self, observer):
        super(ObservabilityPlot, self).__init__()
        self.observer = observer
        

def _console_output_functions(output):
    """Prepare console output functions."""
    if hasattr(output, 'write') and hasattr(output, 'flush'):
        stream = output
    else:
        stream = sys.stdout
    
    def progress():
        if output:
            stream.write(".")
            stream.flush()
            
    def finish():
        if output:
            stream.write("\n")
            stream.flush()
    
    return progress, finish, stream

class VisibilityPlot(EphemerisPlotBase):
    """A single observing night at a specific observatory."""
    
    increment = 6 * u.minute
    
    def __init__(self, observer, date):
        super(VisibilityPlot, self).__init__()
        self.night = Night(observer, date)
        self.targets = list()
        
    def add(self, target):
        """Add a target."""
        if target not in self.targets:
            self.targets.append(target)
    
    def filter_gs_targets(self, sep=(2 * u.arcmin), targetfilter=lambda target : True):
        """Find science targets and eliminate GS/TT targets"""
        targets = {}
        for target in self.targets:
            if not targetfilter(target):
                continue
            if target.name not in targets:
                # Trying a new target.
                found_target = False
                
                for other_target in targets.values():
                    
                    # Only act if we are close to the other target.
                    if other_target.fixed_position.separation(target.fixed_position) <= sep:
                        found_target = True
                        if hasattr(other_target, 'lgs'):
                            continue
                        if hasattr(target, 'lgs'):
                            targets[target.name] = target
                            targets.pop(other_target.name)
                            continue
                        if hasattr(other_target, 'rmag'):
                            targets[target.name] = target
                            targets.pop(other_target.name)
                            continue
                        if hasattr(target, 'rmag'):
                            continue
                        warnings.warn("Two close targets found: {} and {}, can't differentiatie between them. Using first one: {}".format(
                            other_target.name, target.name, other_target.name
                        ))
                if not found_target:
                    targets[target.name] = target
            else:
                warnings.warn("Two targets with the same name found: {!r} and {!r}".format(target, targets[target.name]))
            
        return targets.values()
        
    
    def __call__(self, ax, el=(1.0 * u.degree, 90 * u.degree), unit=u.degree, legend="Outside",
                    moon_distance_spacing=(60 * u.minute), moon_distance_maximum=(30 * u.degree),
                    output=False):
        """Make a visibility plot on a given axes object."""
        ylim_values = (el[0].to(unit).value, el[1].to(unit).value)
        text_el_limit = el[0] + 0.1 * (el[1] - el[0])
        ax_z = self.setup_dual_axis(ax)
        times = self.night.times(self.increment)
        
        progress, finish, stream = _console_output_functions(output)
            
        # Handle the moon.
        moon_pos = []
        altitude_angle = np.zeros((len(times),), dtype=float) * u.degree
        for i, time in enumerate(times):
            self.night.observer.date = time
            moon_pos.append(self.night.moon.position)
            altitude_angle[i] = self.night.moon.alt
        ax.plot(times.datetime, altitude_angle.to(unit).value, 'k--', label=r"Moon", alpha=0.5)
        ax_z.plot(times.datetime, altitude_angle.to(unit).value, 'k--', alpha=0.0)
        
        for target in ProgressBar(self.targets, file=stream):
            altitude_angle = np.zeros((len(times),), dtype=float) * u.degree
            moon_distance = np.zeros((len(times),), dtype=float) * u.degree
            last_moon_distance = self.night.start
            for i,time in enumerate(times):
                self.night.observer.date = time
                target.compute(self.night.observer)
                altitude_angle[i] = target.alt
                moon_distance[i] = moon_pos[i].separation(target.position)
                if ((last_moon_distance + moon_distance_spacing <= time) and 
                    (altitude_angle[i] >= text_el_limit and moon_distance[i] <= moon_distance_maximum)):                    
                    annotate = ax.annotate(
                        s = "{0.value:0.0f} {0.unit:latex}".format(moon_distance[i]),
                        xy = (time.datetime, altitude_angle[i].to(unit).value),
                        xytext = [-5.0, 0.0],
                        textcoords = 'offset points',
                        size = 'x-small',
                        alpha = 0.5)
                    last_moon_distance = time
                
                
            ax.plot(times.datetime, altitude_angle.to(unit).value, '-', label=r"\verb|{}|".format(target.name))
            ax_z.plot(times.datetime, altitude_angle.to(unit).value, ':')
        
        # Sunrise and Sunset lines.
        xmin, xmax = (self.night.start - 1.0 * u.hour), (self.night.end + 1.0 * u.hour)
        ax.set_xlim(xmin.datetime, xmax.datetime)
        ax.axvspan(xmin.datetime, self.night.start.datetime, color='k', alpha=0.2)
        ax.axvspan(xmax.datetime, self.night.end.datetime, color='k', alpha=0.2)
        
        # Label Bright Zones
        ax.text(0.02, 0.5, "Before Sunset", transform=ax.transAxes, va='center', ha='left', rotation=90)
        ax.text(0.98, 0.5, "After Sunrise", transform=ax.transAxes, va='center', ha='right', rotation=90)
        
        # Axis formatting
        ax.grid(True, axis='both')
        ax.xaxis.tick_bottom()
        ax.xaxis.set_label_position('bottom')
        self.format_timezone_axis(ax.xaxis, "UTC", fmt="%H:%M")
        self.format_units_axis(ax.yaxis, unit, "Elevation")
        
        # Add dates to UTC axis.
        ax.text(-0.015, -0.05, "{0.datetime:%Y/%m/%d}".format(self.night.start), transform=ax.transAxes, va='top', ha='right',
            bbox=dict(fc='white', ec='none'))
        ax.text(1.02, -0.05, "{0.datetime:%Y/%m/%d}".format(self.night.end), transform=ax.transAxes, va='top', ha='left',
            bbox=dict(fc='white', ec='none'))
        
        # 2nd Axis Formatting
        ax_z.xaxis.tick_top()
        ax_z.xaxis.set_visible(True)
        ax_z.xaxis.set_label_position('top')
        self.format_timezone_axis(ax_z.xaxis, self.night.observer.timezone, fmt="%H:%M")
        self.format_airmass_axis(ax_z.yaxis, unit)
        
        # Add dates to localtime axis.
        local_tz = self.night.observer.timezone
        utc_tz = pytz.UTC
        local_start = utc_tz.localize(self.night.start.datetime).astimezone(local_tz)
        local_end = utc_tz.localize(self.night.end.datetime).astimezone(local_tz)
        ax.text(-0.015, 1.05, "{0:%Y/%m/%d}".format(local_start), transform=ax.transAxes, va='bottom', ha='right',
            bbox=dict(fc='white', ec='none'))
        ax.text(1.02, 1.05, "{0:%Y/%m/%d}".format(local_end), transform=ax.transAxes, va='bottom', ha='left',
            bbox=dict(fc='white', ec='none'))
        
        ax.text(1+0.35/2, 0.02, "{0:s}".format(self.night.observer.name), transform=ax.transAxes, va='bottom', ha='center',
            bbox=dict(fc='white', ec='none'))
        
        
        # Axis limits
        ax.set_ylim(*ylim_values)
        # We have to keep the 2nd axis limits in sync with the first axis, by hand.
        ax_z.set_ylim(*ax.get_ylim())
        ax_z.set_xlim(*ax.get_xlim())
        
        # Apply the legend.
        legend_bboxes = {
            'Outside' : (0.0, 0.0, 1.35, 1.0), # l b w h
            'Inside' : (0.0, 0.0, 1.0, 1.0),
        }
        
        ax.legend(bbox_to_anchor=legend_bboxes[legend], fontsize=8, title="Targets")
        