# -*- coding: utf-8 -*-
# 
#  fitsfiles.py
#  pynirc2
#  
#  Created by Alexander Rudy on 2013-02-15.
#  Copyright 2013 Alexander Rudy. All rights reserved.
# 
"""
FITSFiles – Management of FITS Files
====================================

This module contains pythonic objects to represent FITS files, as well as the controllers which allow for the command-line interaction with these tools. The primary class is the :class:`FITSHeaderTable`, which is a searchable, filterable collection of FITS Headers.

.. autoclass:: FITSHeaderTable
    :members:

"""
from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

from pyshell.subcommand import SCController, SCEngine
from pyshell.util import query_yes_no, force_dir_path, collapseuser, check_exists, deprecatedmethod

import numpy as np
import astropy.io.fits as pf

import os, os.path, glob, sys
import shlex
import re, ast
import warnings, logging
import datetime
import collections
from textwrap import fill

def silent_getheader(filename):
    """Get the headerfile without validation warnings.
    
    This is a simple wrapper function to silence warnings from PyFITS (which has gotten noisy) and to attempt to ignore inconsistencies in header validation. It seems that many instruments don't write strictly valid FITS headers, which is problematic, but not problematic enough that I want to see a warning every time I try to load one!"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        header = pf.getheader(filename,ignore_missing_end=True).copy()
    return header
    
def silent_getheaders(filename, close=True):
    """Return a list of all headers. Ignore validation warnings and load warnings along the way.
    
    This is a wrapper function which silences warnings from PyFITS and produces a list of all of the headers in a single HDU List object.
    
    :param bool close: Whether to close the HDUlist
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        hdulist = pf.open(filename,ignore_missing_end=True)
        headers = [ hdu.header.copy() for hdu in hdulist ]
        if close:
            hdulist.close()
    return headers
    
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
    """Manages sets of FITS headers, search through them and collect approprate sets of information.
    
    This class behaves like a list of FITS Headers (using pyfits as the header class) which can be filtered using instance methods.
    """
    def __init__(self, iterable=None):
        super(FITSHeaderTable, self).__init__()
        if iterable is not None:
            self += iterable
        
    def __repr__(self):
        """Representation of this object."""
        return "{:s}{:r}".format(self.__class__.__name__, self.files)
    
    @property
    def files(self):
        """A list of filenames in this HeaderTable"""
        return [ header["OPENNAME"] for header in self ]
        
    def copy(self):
        """Return a copy of this object."""
        return self.__class__([ hdr for hdr in self ])
        
    def read(self, files):
        """Get FITS Headers from each file in `files`. This method will load all of the headers for each file (including FITS extension headers).
        
        :param files: The list of file names to be loaded.
        
        """
        for file in files:
            headers = silent_getheaders(file)
            for header in headers:
                if "FILENAME" not in header:
                    header["FILENAME"] = (os.path.basename(file),'Original File name')
                if "OPENNAME" not in header:
                    header["OPENNAME"] = (os.path.relpath(file),'Opened File Name')
                self.append(header)
        
    @classmethod
    def fromfiles(cls, files):
        """Create a FITSHeaderTable from a list of files using :meth:`read`.
        
        :param files: The list of file names to be loaded.
        
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
                        warnings.warn("Couldn't find keyword '%s' in file '%s'" % (key, header["OPENNAME"]))
                    header[key] = blank
        return self
        
    def search(self,**keywords):
        """Search for headers that match specific keyword values.
        
        :param keywords: Arbitrary keyword-style arguments specfiying the search criteria.
        :returns: A new HeaderTable object filtered down.
        
        All searches are performed with the "AND" operator. Keyword arguments should be of the form KEYWORD="search value" where "search value" can be one of the following types:
        - A string or other basic python literal. In this case, the keyword value is matched against the entire literal.
        - A regular expression object from :func:`re.compile`, where :meth:`match` is used to match the compiled regular expression to the keyword value.
        - A boolean value. True means that you only want headers which have the specified keyword. False means you only want headers which **don't** have the specified keyword. For ``False``, the keyword value will be normalized to the empty stirng (for logging/listing purposes).
        
        """ 
        if "OPENNAME" not in keywords:
            keywords["OPENNAME"] = True
        results = self.__class__()
        for header in self:
            keep = True
            for key,search in keywords.iteritems():
                if key not in header and (search is not False):
                    warnings.warn("Couldn't find keyword '%s' in file '%s'" % (key,header["OPENNAME"]))
                    keep = False
                elif hasattr(search,'match'):
                    if not search.match(str(header[key])):
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
    
    def group(self,keys,key_fmt=None):
        """Using a list of keywords, collect groups of headers for which the value of each specified keyword matches among the whole group. This is done using a :class:`FITSDataGroups` object, and such an object is returned. :class:`FITSDataGroups` objects behave like sets, and so can be iterated over. To access individual elements, use the :meth:`FITSDataGroups.get` method."""
        if key_fmt is None:
            key_fmt = []
        self.groups = FITSDataGroups(keys,key_fmt)
        for header in self:
            self.groups.add(header)
        return self.groups
    
    def log(self, order=None):
        """Create a log-file like list of strings from a collection.
        
        :param collection: The collection to use. If ``None``, use the current internal collection.
        
        """
        if order is None:
            order = self[0].keys()
            order.sort()
        if "OPENNAME" in order:
            order.remove("OPENNAME")
        
        # Unfilled Format
        column_format = " {{{}!s:<20.20}} "
        fname_format = " {{{}:<30.30s}}"
        column_line = fname_format + column_format * (len(order))
        
        # List of keys in column order
        key_list = ["OPENNAME"] + order
        header_list = ["file"] + order
        header_data = dict(zip(key_list,header_list))
        
        # Format string ready for formatting
        column_keywords = column_line.format(*key_list)
        
        output = [ column_keywords.format(**header_data) ]
        output += [ column_keywords.format(**header) for header in self ]
        return output

class FITSDataGroups(collections.MutableSet):
    """A set of FITS data groups"""
    
    EMPTYFORMAT = "{!s}"
    
    def __init__(self,keywords,formats="{!s}"):
        super(FITSDataGroups, self).__init__()
        self._groups = {}
        self._keywords = keywords
        if isinstance(formats,list):
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
        hhash = self.type_to_hash(item)
        if hhash not in self.hashes:
            return hhash in [group.name for group in self]
        else:
            return hhash in self.hashes
        
    @property
    def keywords(self):
        """docstring for keywords"""
        return self._keywords
        
    @property
    def formats(self):
        """docstring for formats"""
        return self._formats
        
    @property
    def hashes(self):
        """Return the data group's hashes"""
        return self._groups.keys()
        
    def get(self,hhash,value=None):
        """Return a specific data group"""
        return self._groups.get(hhash,value)
        
    def addlist(self,filename,asgroup=True):
        """Add a list of files as a ListFITSDataGroup"""
        listgroup = ListFITSDataGroup(filename,self.keywords,self.formats)
        if len(headers) > 0 and not self.hasgroup(*listgroup):
            self.add(listgroup)
             
        
        
    def isgroup(self,*headers):
        """Check whether the provided headers constitutes a group here."""
        headers = list(headers)
        header = headers.pop()
        masterhash = self.make_hash(header)
        for header in headers:
            if self.make_hash(header) != masterhash:
                return False
        return True
        
    def hasgroup(self,*headers):
        """Return whether the headers have a group."""
        if self.isgroup(*headers):
            khash = self.make_hash(headers[0])
            if khash in self:
                incfiles = self.get(khash).files
                incfiles.sort()
                hfiles = [ header["FILENAME"] for header in headers ]
                hfiles.sort()
                return hfiles == incfiles
        return False
        
    def islist(self,item):
        """Return whether this item is a list."""
        khash = self.type_to_hash(item)
        return isinstance(self._groups[khash],ListFITSDataGroup)
        
    def addmany(self,*items):
        """Add many items simultaneously."""
        return [ self.add(item) for item in items ]
            
        
    def add(self,item):
        """Add a data group, returning its new hash."""
        
        if isinstance(item,FITSDataGroup):
            if item.keyhash not in self:
                self._groups[item.keyhash] = item
                return item.keyhash
            else:
                raise KeyError("DataGroup with hash {} already exists.".format(item.keyhash))
        hhash = self.type_to_hash(item)
        if item not in self:
            self._groups[hhash] = FITSDataGroup(item, hhash, self.keywords, self.formats)
        else:
            self._groups[hhash].append(item)
        return hhash
        
    def type_to_hash(self,item):
        """docstring for type_to_hash"""
        if isinstance(item,basestring) and check_exists(item) and item.endswith(".fits"):
            item = silent_getheader(item)
        if isinstance(item,pf.header.Header) or isinstance(item,collections.Mapping):
            hhash = self.make_hash(item)
        elif isinstance(item,basestring):
            hhash = unicode(item)
        else:
            raise TypeError("Can't convert {} to Header Hash".format(type(item)))
        return hhash
        
    def make_hash(self,dictionary):
        """Make the appropraite keyword hash for a given dictionary"""
        return unicode("".join([ unicode(key)+u"="+unicode(dictionary[key]) for key in self.keywords ]))
        
    def discard(self,item):
        """Discard a group from this group set."""
        hhash = self.type_to_hash(item)
        del self._groups[hhash]
        
    def table(self):
        """Return a text table for this datagroup"""
        col = "{:<20}"
        row = "{:<30.30s}" + (col * (len(self.keywords)))
        head = row.format("Name",*[keyword for keyword in self.keywords]) + "  N"
        txt_row = "{{:<{}s}}".format(len(head)-6) + "{:>3d}"
        row = row + "{:>3d}"
        hashes = self.hashes
        hashes.sort()
        output = [head,"-"*(len(head))]
        for keyhash in hashes:
            if self.islist(keyhash):
                output += [txt_row.format(keyhash,len(self.get(keyhash)))]
            else:
                rowtuple = [self.get(keyhash).name]
                for keyword in self.keywords:
                    rowtuple.append(self.get(keyhash).keylist[keyword])
                rowtuple.append(len(self.get(keyhash).files))
                output += [row.format(*rowtuple)]
        return output

class FITSDataGroup(FITSHeaderTable):
    """docstring for FITSDataGroup"""
    def __init__(self,header,keyhash,keywords,formats):
        """docstring for __init__"""
        super(FITSDataGroup, self).__init__([header])
        self._keyhash = keyhash
        self._keywords = keywords
        self._formats = formats
    
    @property
    def keywords(self):
        """docstring for keyword"""
        return self._keywords
    
    @property
    def keylist(self):
        """Get the uniform keylist for this object."""
        return { key:self[0][key] for key in self.keywords }
        
    @property
    def keyhash(self):
        return self._keyhash
        
    @property
    def name(self):
        """Return the formatted name"""
        return "-".join([ _format.format(self.keylist[keyword]) for _format,keyword in zip(self._formats, self.keywords) ]).replace(" ","-")
    
        
class ListFITSDataGroup(FITSDataGroup):
    """A group of FITS files defined by an input list."""
    def __init__(self,listfile,keywords,formats):
        super(ListFITSDataGroup, self).__init__(header=None,keyhash=listfile,keywords=keywords,formats=formats)
        self.read(readfilelist(listfile))
        self._list = listfile
        
    @property
    def name(self):
        """FormattedName"""
        return os.path.basename(os.path.splitext(self._list)[0])
        
    @property
    def filename(self):
        """Return the full filename"""
        return self._list
        
    @property
    def keyhash(self):
        """Return the proper keyhash"""
        return os.path.basename(self.filename)
        
    @property
    def keylist(self):
        """The master list of keys doesn't make sense for an arbitrary list."""
        raise ValueError("The Master List of Keys can't be retrieved from a list.")
        


class FITSCLI(SCEngine):
    """A base class for command line interfaces using pyshell."""
    
    options = []
    
    def after_configure(self):
        """Configure the logging"""
        super(FITSCLI, self).after_configure()
        if "i" in self.options:
            self.parser.add_argument('-i','--input',help="Either a glob or a list contianing the files to use.",
                action='store',nargs="+",type=unicode,default=unicode(self.config.get("Defaults.Log.Glob","*.fits")))
        if "o" in self.options:
            self.parser.add_argument('-o','--output',help="Output file name",
                default=self.config.get("Defaults.Log.OutputName",False),action='store',dest='output')
        if "skw" in self.options:
            self.parser.add_argument('--re',action='store_true',
                help="Use regular expressions to parse header values.")
            self.parser.add_argument('keywords',nargs="*",action='store',
                help="File Header search keywords. 'KWD' is the FITS header keyword to seach for, and 'value' is the search value. See `--re` to use 'value' as a regular expression.",metavar='KWD=value')
        if "gkw" in self.options:
            self.parser.add_argument('keywords',nargs="*",help="Keywords to group.",action='store',default=self.config.get("Log.Keywords"))
            
                
            
        
    def get_files(self):
        """Get the list of files used by the -i command line argument."""
        from pyshell.util import check_exists, warn_exists
        if check_exists(self.opts.input):
            files = readfilelist(self.opts.input)
        else:
            infiles = shlex.split(self.opts.input)
            files = []
            for infile in infiles:
                files += glob.glob(infile)
        for file in files:
            warn_exists(file,"FITS File",True) 
        return files
        
    def get_keywords(self):
        """Get the dictionaries for search keywords"""
        search = collections.OrderedDict()
        for pair in self.opts.keywords:
            if len(pair.split("=",1)) == 2:
                key,value = pair.split("=",1)
                if self.opts.re:
                    value = re.compile(value)
                else:
                    try:
                        value = ast.literal_eval(value)
                    except:
                        value = value
            elif len(pair.split("=")) == 1:
                key,value = pair,True
            else:
                self.parser.error("Argument for Malformed Keyword Pair: '%s'" % pair)
            search[key] = value
        return search
        
class FITSShow(FITSCLI):
    """Show information about a fits file"""
    
    command = 'show'
    
    help = "Show details about a group of FITS files."
    
    description = fill("Shows the full header for the fits files found.")
    
    options = [ "i", "o", "skw" ]
    
    def do(self):
        """Do the work"""
        files = self.get_files()
        search = self.get_keywords()
        data = FITSHeaderTable.fromfiles(files).search(**search)
        print("Will get info on %d files." % len(data))
        if self.opts.output is False:
            self.opts.output = None
        [ pf.info(header["OPENNAME"], self.opts.output) for header in data ]
                

class FITSGroup(FITSCLI):
    """Create a list of groups from FITS header attributes."""
    
    command = 'group'
    
    help = "Make a list of groups for a collection of FITS files."
    
    description = fill("Creates a text table with the requested header information grouped for a bunch of FITS files. Groups are collections of files which have identical header values. Files can be filtered before grouping using the 'KEYWORD=value' search syntax.")
        
    options = [ "i", "skw" ]        
        
    def do(self):
        """Make the log table"""
        files = self.get_files()
        search = self.get_keywords()
        print("Will group %d files." % len(files))
        data = FITSHeaderTable.fromfiles(files).search(**search).group(search.keys())
        output = data.table()
        print("\n".join(output))
        print("%d files grouped." % len(data))

class FITSLog(FITSCLI):
    """Create a log from FITS header attributes."""
    
    command = 'log'
    
    options = [ "i", "o", "skw" ]
    
    help = "Make a log file for a collection of FITS files."
    
    description = fill("Creates a text table with the requested header information for a bunch of FITS files.")
        
    def do(self):
        """Make the log table"""
        from pyshell.util import check_exists
        if self.opts.output and check_exists(self.opts.output):
            print("Log %r already exists. Will overwirte." % self.opts.output)
        
        files = self.get_files()
        search = self.get_keywords()
        
        print("Will log %d files." % len(files))
        data = FITSHeaderTable.fromfiles(files).search(**search).normalize(search.keys())
        output = data.log(order=search.keys())
        if self.opts.output:
            with open(self.opts.output,'w') as outputfile:
                outputfile.write("\n".join(output))
        else:
            print("\n".join(output))
            print("%d files found." % len(data))
        
        
    
    
class FITSList(FITSCLI):
    """Make a list of files with certain header attributes"""
    
    command = "list"
    
    options = [ "i", "skw" ]
    
    help = "Make a list of FITS files that match criteria."
    
    description = "Make a list of FITS files that match given criteria using direct matching, substring matching, or regular expressions."
    
    def after_configure(self):
        super(FITSList, self).after_configure()
        self.parser.add_argument('-o','--output',action='store',
            default=self.config.get("Defaults.List.Name",False),help="Output list file name.",metavar="files.list")
        self.parser.add_argument('-l','--log',action='store_true',
            help="Store a full log file, not just a list of files that match this keyword.")
        
            
    def do(self):
        """Run the search itself"""
        search = self.get_keywords()
        files = self.get_files()
        print("Searching %d files." % len(files))
        data = FITSHeaderTable.fromfiles(files).normalize(search.keys()).search(**search)
        output = data.log(order=search.keys())
        print("\n".join(output))
        print("%d files found." % len(output))
        
        if self.opts.output:
            if not self.opts.log:
                output = data.files
            with open(self.opts.output,'w') as fnamelist:
                fnamelist.write("\n".join(output))
            print("Wrote file %s to '%s'" % ("log" if self.opts.log else "list",self.opts.output))
        
