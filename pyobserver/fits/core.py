# -*- coding: utf-8 -*-
#
#  fitsfiles.py
#  pynirc2
#
#  Created by Alexander Rudy on 2013-02-15.
#  Copyright 2013 Alexander Rudy. All rights reserved.
#
"""
:mod:`FITSFiles` – Management of FITS Files
===========================================

This module contains pythonic objects to represent FITS files, as well as the controllers which allow for the command-line interaction with these tools. The primary class is the :class:`FITSHeaderTable`, which is a searchable, filterable collection of FITS Headers.

Working with collections of headers
-----------------------------------

This is the primary working class for dealing with collections of FITS headers.

.. autoclass:: FITSHeaderTable
    :members:
    :inherited-members:

Grouping FITS Files
-------------------
FITS files can be grouped by the values found in header keywords. The grouping ensures that all headers have the same values for the given keywords. Grouping can be used to collect all of the FITS files which use a given filter, are of a given target, and have a given exposure time. The grouping provides a nice summary of different observations within a collection of FITS files. The :class:`FITSDataGroups` is returned from :meth:`FITSHeaderTable.group`, and manages grouping FITS files.

.. autoclass:: FITSDataGroups
    :members:


Homogenous Groups
*****************

Groups created automatically by :class:`FITSDataGroups` will all be *Homogenous Groups*. Homogenous groups are sets of FITS headers where all headers have matching keyword values for the group keywords. Homogenous groups are a subclass of :class:`FITSHeaderTable`, and so can be used for sorting, pretty-printing, and logging individual groups of files.

.. autoclass:: FITSDataGroup
    :members:
    :inherited-members:


Non-Homogenous Groups
*********************
Groups can also include non-homogenous groups, which are generally lists of files that are joined.

.. autoclass:: ListFITSDataGroup
    :members:
    :inherited-members:
    


"""
from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

from pyshell.subcommand import SCController, SCEngine
from pyshell.util import query_yes_no, force_dir_path, collapseuser, check_exists, deprecatedmethod

import numpy as np

try:
    import astropy.io.fits as pf
except ImportError as e:
    try:
        import pyfits as pf
    except ImportError:
        raise e

import os, os.path, glob, sys
import shlex
import re, ast
import warnings, logging
import datetime
import collections
from textwrap import fill
import six

try:
    import cStringIO as io
except ImportError:
    import StringIO as io


def silent_getheader(filename):
    """Get the headerfile without validation warnings.
    
    This is a simple wrapper function to silence warnings from PyFITS (which has gotten noisy) and to attempt to ignore inconsistencies in header validation. It seems that many instruments don't write strictly valid FITS headers, which is problematic, but not problematic enough that I want to see a warning every time I try to load one!"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        header = pf.getheader(filename,ignore_missing_end=True).copy()
        header.filename = filename
    return header, filename

def silent_getheaders(filename, close=True):
    """Return a list of all headers. Ignore validation warnings and load warnings along the way.
    
    This is a wrapper function which silences warnings from PyFITS and produces a list of all of the headers in a single HDU List object.
    
    :param bool close: Whether to close the HDUlist
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        hdulist = pf.open(filename,ignore_missing_end=True)
        headers = [ hdu.header.copy() for hdu in hdulist ]
        map(lambda h : setattr(h,'filename',filename), headers)
        if close:
            hdulist.close()
    return [(header, filename) for header in headers]

def readfilelist(filename):
    """Read a file list and provide the list of files."""
    dirname = os.path.dirname(filename)
    files = []
    with open(filename,'r') as stream:
        for line in stream:
            fname = os.path.join(dirname,line.rstrip("\n"))
            if not line.startswith("#"):
                files.append(fname)
    return files

class FITSHeaderTable(list):
    """Manages sets of FITS headers, search through them and collect approprate sets of information. This class behaves like a list of FITS Headers (using pyfits as the header class) which can be filtered using instance methods. It can be initialized with an iterable that contains :mod:`~astropy.io.fits.hdu.Header` objects.
    
    :param iterable: Something with which to initialize this list.
    
    .. note:: Most methods that operate on :class:`FITSHeaderTable` objects return new :class:`FITSHeaderTable` objects (i.e. they are **not** in-place.)
    """
    def __init__(self, iterable=None):
        super(FITSHeaderTable, self).__init__()
        if iterable is not None:
            self += iterable
    
    def __repr__(self):
        """Representation of this object."""
        return "{:s}{:r}".format(self.__class__.__name__, self.files)
        
    def __setitem__(self, key, value):
        """Set a list item, ensuring it is a header, and that it understands its own filename."""
        if not isinstance(value, pf.header):
            raise TypeError("FITSHeaderTables should contain only FITS Headers. Got '{}' instead".format(type(value)))
        if not hasattr(value, 'filename'):
            if "OPENNAME" in value:
                value.filename = os.path.abspath(value["OPENNAME"])
            elif "FILENAME" in value:
                value.filename = os.path.abspath(value["FILENAME"])
        return super(FITSHeaderTable, self).__setitem__(key, value)
        
    
    @property
    def files(self):
        """A list of filenames in this :class:`FITSHeaderTable`."""
        files = []
        for header in self:
            if header.filename not in files:
                files.append(header.filename)
        return files
        
    def filelist(self, filename):
        """Make a file list at the given filename, which should contain all the FITS filenames here."""
        with open(filename, 'w') as stream:
            stream.write("\n".join(map(os.path.relpath,self.files)))
            stream.write("\n")
        return filename
        
    def prefix_filelist(self, filename, prefix):
        """Insert a prefix on each filename."""
        files = [ os.path.split(os.path.relpath(f)) for f in self.files ]
        files = [ os.path.join(base, prefix+name) for base, name in files ]
        with open(filename, 'w') as stream:
            stream.write("\n".join(files))
        return filename
    
    def copy(self):
        """Return a copy of this object."""
        return self.__class__([ hdr for hdr in self ])
    
    def read(self, files):
        """Get FITS Headers from each file in `files`. This method will load all of the headers for each file (including FITS extension headers).
        
        :param files: The list of file names to be loaded.
        :return: `self` - this is an *in-place* operation.
        
        """
        for file in files:
            headers = silent_getheaders(file)
            for header, filename in headers:
                if "FILENAME" not in header:
                    header["FILENAME"] = (os.path.basename(file), 'Original File name')
                if "OPENNAME" not in header:
                    header["OPENNAME"] = (os.path.relpath(file), 'Opened File Name')
                self.append(header)
        return self
    
    @classmethod
    def fromfiles(cls, files):
        """Create a :class:`FITSHeaderTable` from a list of files using :meth:`read`.
        
        :param files: The list of file names to be loaded.
        :return: A new :class:`FITSHeaderTable` object.
        
        """
        obj = cls()
        obj.read(files)
        return obj
    
    
    def normalize(self,keywords,blank="",warn=True,error=False):
        """Collect and normalize a set of headers by keyword.
        
        :param keywords: The keywords to search for.
        :param string blank: The blank value fill missing keywords.
        :param bool warn: Whether to raise a warning for missing keywords.
        :param bool error: Whether to raise a :exc:`KeyError` for missing keywords.
        :returns: A reference to this object.
        
        This function ensures that each collected header contains a minimal value for every requested keyword. The minimum value is by default the empty string. The function will raise a warning if the requested keyword is not present."""
        keywords = list(keywords)
        if "OPENNAME" not in keywords:
            keywords.append("OPENNAME")
        for header in self:
            for key in keywords:
                if key not in header:
                    if error:
                        raise KeyError("Keyword '%s' not in file '%s'" % (key, header["OPENNAME"]))
                    if warn:
                        pass
                        # warnings.warn("Couldn't find keyword '%s' in file '%s'" % (key, header["OPENNAME"]))
                    header[key] = blank
        return self
    
    def search(self,**keywords):
        """Search for headers that match specific keyword values.
        
        :param keywords: Arbitrary keyword-style arguments specifying the search criteria.
        :returns: A new :class:`FITSHeaderTable` object filtered down.
        
        All searches are performed with the "AND" operator. Keyword arguments should be of the form KEYWORD="search value" where "search value" can be one of the following types:
        
        - A string or other basic python literal. In this case, the keyword value is matched against the entire literal.
        - A regular expression object from :func:`re.compile`, where :meth:`match` is used to match the compiled regular expression to the keyword value.
        - A boolean value. ``True`` means that you only want headers which have the specified keyword. ``False`` means you only want headers which **don't** have the specified keyword. For ``False``, the keyword value will be normalized to the empty string (for logging/listing purposes).
        
        """
        if "OPENNAME" not in keywords:
            keywords["OPENNAME"] = True
        results = self.__class__()
        for header in self:
            keep = True
            for key,search in keywords.iteritems():
                if key not in header and (search is True):
                    # warnings.warn("Couldn't find keyword '%s' in file '%s'" % (key,header.filename))
                    keep = False
                elif search is None:
                    header.setdefault(key, "")
                elif hasattr(search,'match'):
                    if not search.match(str(header[key])):
                        keep = False
                elif callable(search):
                    try:
                        keep = search(header[key])
                    except Exception as e:
                        warnings.warn("Callable keyword search failed at file '{}': {}".format(header.filename, e))
                        keep = False
                elif isinstance(search,bool):
                    if search and key in header:
                        pass
                    elif (not search) and (key not in header):
                        header[key] = ""
                    else:
                        keep = False
                elif search == header[key]:
                    pass
                else:
                    keep = False
            if keep:
                results.append(header)
        return results
    
    def group(self, keywords, key_fmt=None):
        """Using a list of keywords, collect groups of headers for which the value of each specified keyword matches among the whole group. This is done using a :class:`FITSDataGroups` object, and such an object is returned. :class:`FITSDataGroups` objects behave like sets, and so can be iterated over. To access individual elements, use the :meth:`FITSDataGroups.get` method.
        
        :param list keywords: This should be a list of keywords which will be used to group the FITS headers.
        :param list key_fmt: This is an optional list of format strings to control the pretty-printing of each header keyword.
        :return: A :class:`FITSDataGroups` object.
        
        """
        if key_fmt is None:
            key_fmt = []
        groups = FITSDataGroups(keywords,key_fmt)
        for header in self:
            groups.add(header)
        return groups
    
    def table(self, order=None):
        """Create a log-file like list of strings from a collection.
        
        :param collection: The collection to use. If ``None``, use the current internal collection.
        
        """
        from astropy.table import Table
        
        if order is None:
            order = self[0].keys()
            order.sort()
        if "OPENNAME" in order:
            order.remove("OPENNAME")
        
        # List of keys in column order
        key_list = ["OPENNAME"] + order
        header_list = [str("file")] + order
        header_list = map(str, header_list)
        
        data_list = [ [ header[key] for header in self ] for key in key_list ]
        
        table = Table(data_list, names = header_list)
        return table

class FITSDataGroups(collections.MutableSet):
    """A set of FITS data groups, defined by the operable `keywords`. The set of `keywords` will have identical values for each group.
    
    :param list keywords: A list of FITS header keywords to use to group files.
    :param list formats: A list of format strings (new-style), which take a single argument (the keyword value) and convert it to an appropriate string.
    
    When `formats` is not provided, ``{!s}`` is used. If `formats` is shorter than `keywords`, any extra values will be filled in by the :attr:`EMPTYFORMAT` attribute.
    
    This object will behave like a mutable set of FITS header objects. New header objects can be added to the set. When they are added, they will either become a member of an existing group, or will create a new group.
    
    """
    
    EMPTYFORMAT = "{!s}"
    
    def __init__(self, keywords, formats="{!s}", md5=False):
        super(FITSDataGroups, self).__init__()
        self._md5 = md5
        self._groups = {}
        self._keywords = keywords
        if isinstance(formats, list):
            _formats = formats
        else:
            _formats = [formats]
        if len(self._keywords) > len(_formats):
            _formats += [self.EMPTYFORMAT] * (len(self._keywords) - len(_formats))
        self._formats = []
        for _format in _formats:
            if _format is None:
                self._formats.append(self.EMPTYFORMAT)
            else:
                self._formats.append(_format)
        
    
    def __iter__(self):
        """Iterable"""
        return self._groups.itervalues()
    
    def __len__(self):
        """Length"""
        return self._groups.__len__()
    
    def __contains__(self,item):
        """Check if this FITSDataGroups contains a specific item. Forms of item:
        
        pyfits header
        dictionary of header keywords and values
        string keyhash
        string groupname
        string filename
        """
        hhash = self._make_hash(item)
        if hhash not in self.hashes:
            return hhash in [group.name for group in self]
        else:
            return hhash in self.hashes
    
    @property
    def keywords(self):
        """The list of keywords used to group these files."""
        return self._keywords
    
    @property
    def formats(self):
        """The list of format strings used to print keywords."""
        return self._formats
    
    @property
    def hashes(self):
        """The list of hashes of data groups."""
        return self._groups.keys()
        
    @property
    def homogenous(self):
        """Whether this object only contains homogenous groups."""
        return not any([isinstance(group, ListFITSDataGroup) for group in self ])
    
    def get(self,hhash,value=None):
        """Return a specific data group, by hash.
        
        :param string hhash: The desired group's hash value.
        :param value: A default value to return.
        
        """
        return self._groups.get(hhash,value)
    
    def addlist(self, filename, asgroup=True):
        """Add a list of files as a :class:`ListFITSDataGroup`, where the files don't have to be a true homogenous group.
        
        :param string filename: The file name of the FITS list file.
        :return: The hash string for the new group.
        
        """
        
        if not asgroup:
            return self.addmany(*readfilelist(listfile))
        listgroup = ListFITSDataGroup(filename, self.keywords, self.formats)
        if len(listgroup) > 0 and not self.hasgroup(*listgroup):
            self.add(listgroup)
        
        
    
    def isgroup(self, *headers):
        """Check whether the provided headers constitutes a group.
        
        :param headers: Any number of headers which might be a group.
        :return: Whether these headers are a homogenous group.
        
        """
        headers = list(headers)
        header = headers.pop()
        masterhash = self._build_hash(header)
        for header in headers:
            if self._build_hash(header) != masterhash:
                return False
        return True
    
    def hasgroup(self, *headers):
        """Check whether the headers belong to any existing group. If all of the headers belong to a single existing group, and no more, then this is a group.
        
        :param headers: Any number of headers which might be a group.
        :return: Whether these headers consist of an existing homogenous group.
        
        """
        if self.isgroup(*headers):
            khash = self._build_hash(headers[0])
            if khash in self:
                incfiles = self.get(khash).files
                incfiles.sort()
                hfiles = [ header.filename for header in headers ]
                hfiles.sort()
                return hfiles == incfiles
        return False
    
    def islist(self,item):
        """Check whether the given item is a list. The `item` can be a header or a group which already exists in this object.
        
        :param item: Any item which can be made into a group hash. (see :meth:`add`)
        
        """
        khash = self._make_hash(item)
        return isinstance(self._groups[khash],ListFITSDataGroup)
    
    def addmany(self, *items):
        """Add many items simultaneously.
        
        :param items: The items to add.
        :return: A list of hashes that were added to the data groups.
        
        """
        return [ self.add(item) for item in items ]
        
    
    def add(self,item):
        """Add a new item.
        
        :param item: Any item which can be added to this set.
        :return: The hash labeling the group to which this item was added.
        
        Valid `item` types:
        
        - A filename to an existing FITS file.
        - A :class:`~astropy.io.fits.hdu.Header` object.
        - A dictionary mapping that looks like a header.
        
        """
        
        if isinstance(item, FITSDataGroup):
            if item.keyhash not in self:
                self._groups[item.keyhash] = item
                return item.keyhash
            else:
                raise KeyError("DataGroup with hash {} already exists.".format(item.keyhash))
        
        hhash = self._make_hash(item)
        if item not in self:
            self._groups[hhash] = FITSDataGroup(item, hhash, self.keywords, self.formats)
        else:
            self._groups[hhash].append(item)
        return hhash
    
    def _make_hash(self, item):
        """Convert an item into a hash for this object. This method is mostly used internally, but can be used to get the hash of any item as it would be constructed by this grouping.
        
        :param item: An item to convert to a hash.
        :return: The hash.
        
        Valid `item` types:
        
        - A filename to an existing FITS file.
        - A :class:`~astropy.io.fits.hdu.Header` object.
        - A dictionary mapping that looks like a header.
        - A string hash (returned unchanged, but unicode encoded)
        
        """
        if isinstance(item, FITSDataGroup):
            return item.keyhash
        
        if isinstance(item, six.string_types) and check_exists(item) and item.endswith(".fits"):
            item = silent_getheader(item)
        if isinstance(item, pf.header.Header) or isinstance(item, collections.Mapping):
            hhash = self._build_hash(item)
        elif isinstance(item, six.string_types):
            hhash = six.text_type(item)
        else:
            raise TypeError("Can't convert {} to Header Hash".format(type(item)))
        return hhash
    
    def _build_hash(self, dictionary):
        """Make the appropriate keyword hash for a given dictionary.
        
        :param dictionary: Any mapping with the correct keyword set that can be used to construct a hash.
        :return: The hash.
        
        """
        value = six.text_type(":".join([ six.text_type(key) + "=" + six.text_type(dictionary[key]) for key in self.keywords ]))
        if self._md5:
            import hashlib
            hashcontainer = hashlib.md5()
            hashcontainer.update(value)
            value = hashcontainer.hexdigest()
        return value
    
    def discard(self, item):
        """Discard a group from this group set.
        
        :param item: Any item which can be used to look up a group.
        
        """
        hhash = self._make_hash(item)
        del self._groups[hhash]
    
    def table(self, filter_homogenous=False):
        """Return a text table for this datagroup. See :meth:`output`.
        
        .. note:: This method currently returns a list of strings. In the future, it will return an :class:`astropy.table.Table` object containing only the desired header keywords.
        
        """
        from astropy.table import Table, Column
                
        if filter_homogenous:
            groups = [ group for group in self if not isinstance(group, ListFITSDataGroup) ]
            list_groups = []
        else:
            groups = [ group for group in self if not isinstance(group, ListFITSDataGroup) ]
            list_groups = [ group for group in self if isinstance(group, ListFITSDataGroup) ]
            
        groups.sort(key=lambda g : g.name)
        
        result = Table([ group.keylist for group in groups ], names=map(str, self.keywords))
        
        name_column = Column(name=str("Name"), data=[ group.name for group in groups ])
        result.add_column(name_column, index=0)
        
        number_column = Column(name=str("N"), data=[ len(group) for group in groups ])
        result.add_column(number_column)
        
        for lgroup in list_groups:
            result.add_row({"Name":lgroup.name, "N":len(lgroup)})
        
        return result

class FITSDataGroup(FITSHeaderTable):
    """A single homogenous group of FITS files. The files are required to be homogenous. A single header is required to create this group.
    
    :param header: A FITS header.
    :param keyhash: The full key hash that uniquely identifies this group.
    :param keywords: The keywords used to create the keyhash.
    :param formats: The formatting strings used for each keyword.
    
    """
    def __init__(self,header,keyhash,keywords,formats):
        super(FITSDataGroup, self).__init__([header])
        self._keyhash = keyhash
        self._keywords = keywords
        self._formats = formats
    
    @property
    def keywords(self):
        """The keywords used for this group."""
        return self._keywords
    
    @property
    def keylist(self):
        """A dictionary of the homogenous keys for this group."""
        return { key:self[0][key] for key in self.keywords }
    
    @property
    def keyhash(self):
        """The string hash value for this group."""
        return self._keyhash
    
    @property
    def name(self):
        """A pretty-formatted name of this group, suitable as a filename."""
        return "-".join([ _format.format(self.keylist[keyword]) for _format,keyword in zip(self._formats, self.keywords) ]).replace(" ","-")
        

class ListFITSDataGroup(FITSDataGroup):
    """A group of FITS files defined by an input list, which are usually *not* homogenous.
    
    :param string listfile: The name of a file which lists one FITS file per line.
    :param keywords: The keywords being used by the master grouping.
    :param 
    
    """
    def __init__(self, listfile, keywords, formats):
        super(ListFITSDataGroup, self).__init__(header=None,keyhash=listfile,keywords=keywords,formats=formats)
        del self[0]
        self.read(readfilelist(listfile))
        self._list = listfile
    
    @property
    def name(self):
        """The formatted name of this list. It is the basename of the list filename, without the extension."""
        return os.path.basename(os.path.splitext(self._list)[0])
    
    @property
    def filename(self):
        """Return the full filename."""
        return self._list
    
    @property
    def keyhash(self):
        """The keyhash used to look up this object. It is the basename of the list filename."""
        return os.path.basename(self.filename)
    
    @property
    def keylist(self):
        """The master list of keys. This could be arbitrary for a :class:`ListFITSDataGroup`. Instead, this property will raise a :exc:`ValueError`."""
        raise ValueError("The Master List of Keys can't be retrieved from a ListFITSDataGroup.")


