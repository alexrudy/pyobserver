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

This module contains pythonic objects to represent FITS files, as well as the controllers which allow for the command-line interaction with these tools.

.. autoclass:: 

"""
from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

from pyshell.subcommand import SCController, SCEngine
from pyshell.util import query_yes_no, force_dir_path, collapseuser, check_exists

import numpy as np
import pyfits as pf

import os, os.path, glob, sys
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
        header = pf.getheader(filename,ignore_missing_end=True)
    return header
    
def silent_getheaders(filename, close=True):
    """Return a list of all headers. Ignore validation warnings."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        hdulist = pf.open(filename,ignore_missing_end=True)
        headers = [ hdu.header for hdu in hdulist ]
        hdulist.close()
    return headers
    
class FITSHeaderTable(list):
    """Manages sets of FITS headers, search through them and collect approprate sets of information."""
    def __init__(self):
        super(FITSHeaderTable, self).__init__()
        self._headers = [] # Original list, to prevent re-reading data.
        
    @property
    def collection(self):
        """The collected (and possibly filtered) set of files."""
        return self
        
    @property
    def files(self):
        """A list of filenames in this HeaderTable"""
        return [ header["OPENNAME"] for header in self ]
        
    def copy(self):
        """Return a copy of this object."""
        return self.__class__([ hdr for hdr in self ])
        
    def glob(self,globstring):
        """Use shell-style globbing (from :mod:`glob`) to read file headers."""
        self.read( glob.glob(globstring) )
        
    def read(self, files=None):
        """Get FITS Headers from each file in the `files` list (or stored from a call to :meth:`glob`).
        
        Files read in this method will appear in :attr:`collection` and :attr:`headers` as pyfits Header objects.
        
        :param files: The list of files to be loaded. If ``None``, use the prepared internal list of files.
        :param bool reset: ``True`` (default) will reset, not append to, the internal list of headers.
        """
        with warnings.catch_warnings(record=True) as wlist:
            for file in files:
                headers = silent_getheaders(file)
                for header in headers:
                    if "FILENAME" not in header:
                        header["FILENAME"] = (os.path.basename(file),'Original File name')
                    if "OPENNAME" not in header:
                        header["OPENNAME"] = (os.path.relpath(file),'Opened File Name')
                    self.append(header)
        
        
    def collect(self,*keywords):
        """Backwards compatibility for normalize header functions."""
        return self.normalize(keywords,blank="",warn=True,error=False)
    
    def normalize(self,keywords,blank="",warn=True,error=False):
        """Collect and normalize a set of headers by keyword.
        
        :args keywords: The keywords to search for.
        
        This function ensures that each collected header contains a minimal value for every requested keyword. The minimum value is by default the empty string. The function will raise a warning if the requested keyword is not present. This function acts on :attr:`collection` and returns the collection"""
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
        
        All searches are performed with the "AND" operator. Keyword arguments should be of the form KEYWORD="search value" where "search value" can be one of the following types:
        - A string or other basic python literal. In this case, the keyword value is matched against the entire literal.
        - A regular expression object from :func:`re.compile`, where :meth:`match` is used to match the compiled regular expression to the keyword value.
        - A boolean value. True means that you only want headers which have the specified keyword. False means you only want headers which **don't** have the specified keyword. For ``False``, the keyword value will be normalized to the empty stirng (for logging/listing purposes). """ 
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
                    if search.match(str(header[key])):
                        keep = True
                elif isinstance(search,bool):
                    if search and key in header:
                        keep = True
                    elif (not search) and (key not in header):
                        header[key] = ""
                        keep = True
                    else:
                        keep = False
                elif search == header[key]:
                    keep = True
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
    
    def logstring(self, order=None):
        """Create a log-file like string from a collection.
        
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
        
    
    def liststring(self):
        """Return a list of filenames from a collection."""
        return self.files

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
        _files = []
        with open(filename,'r') as stream:
            for line in stream:
                fname = os.path.join(os.path.dirname(filename),line.rstrip("\n"))
                if not line.startswith("#") and os.path.exists(fname):
                    _files.append(fname)
        FHT = FITSHeaderTable()
        headers = FHT.read(_files)
        if len(headers) > 0 and not self.hasgroup(*headers):
            self.add(ListFITSDataGroup(filename,headers,self.keywords,self.formats))
             
        
        
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
            self._groups[hhash] = FITSDataGroup(item,hhash,self.keywords,self.formats)
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

class FITSDataGroup(collections.MutableSequence):
    """docstring for FITSDataGroup"""
    def __init__(self,header,keyhash,keywords,formats):
        """docstring for __init__"""
        super(FITSDataGroup, self).__init__()
        self._keyhash = keyhash
        self._keywords = keywords
        self._formats = formats
        self._headers = [header]
        
    def __contains__(self,value):
        return value in self._headers
    
    def __iter__(self):
        return iter(self._headers)
        
    def append(self,header):
        self._headers += [header]
        
    def __setitem__(self,key,value):
        return self._headers.__setitem__(key,value)
        
    def __getitem__(self,key):
        return self._headers.__getitem__(key)
        
    def __delitem__(self,key):
        return self._headers.__delitem__(key)
        
    def __len__(self):
        return len(self._headers)
        
    def insert(self,index,value):
        return self._headers.insert(index,value)
    
    @property
    def keywords(self):
        """docstring for keyword"""
        return self._keywords
    
    @property
    def keylist(self):
        """Get the uniform keylist for this object."""
        return { key:self._headers[0][key] for key in self.keywords }
        
    @property
    def keyhash(self):
        return self._keyhash
        
    @property
    def name(self):
        """Return the formatted name"""
        return "-".join([ format.format(self.keylist[keyword]) for format,keyword in zip(self._formats,self.keywords) ]).replace(" ","-")
        
    @property
    def files(self):
        """docstring for files"""
        return [ header["FILENAME"] for header in self._headers ]
        
class ListFITSDataGroup(FITSDataGroup):
    """A group of FITS files defined by an input list.ListFITSDataGroup"""
    def __init__(self,listfile,headers,keywords,formats):
        super(ListFITSDataGroup, self).__init__(header=headers[0],keyhash=listfile,keywords=keywords,formats=formats)
        self._headers = headers
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
            self.parser.add_argument('-i','--input',help="Either a glob or a list contianing the files to use.",action='store',nargs="+",type=unicode,default=unicode(self.config.get("Defaults.Log.Glob","*.fits")))
        if "o" in self.options:
            self.parser.add_argument('-o','--output',help="Output file name",default=self.config.get("Defaults.Log.OutputName",False),action='store',dest='output')
        if "skw" in self.options:
            self.parser.add_argument('--re',action='store_true',
                help="Use regular expressions to parse header values.")
            self.parser.add_argument('keywords',nargs="*",action='store',
                help='File Header search keywords. The "=" and "value" is an optional search argument.',metavar='KWD=value')
        if "gkw" in self.options:
            self.parser.add_argument('keywords',nargs="*",help="Keywords to group.",action='store',default=self.config.get("Log.Keywords"))
            
                
            
        
    def get_files(self):
        """Get the list of files used by the -i command line argument."""
        from pyshell.util import check_exists, warn_exists
        if check_exists(self.opts.input):
            with open(self.opts.input, 'r') as inlist:
                files = [ line.rstrip("\n\r") for line in inlist ]
        else:
            infiles = self.opts.input.split()
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
    
    help = "Show details about the first found fits file."
    
    description = fill("Shows the full header for the first fits file found.")
    
    options = [ "i", "o", "skw" ]
    
    def do(self):
        """Do the work"""
        files = self.get_files()
        search = self.get_keywords()
        data = FITSHeaderTable()
        data.read(files)
        print("Will get info on %d files." % len(data.collection))
        if self.opts.output is False:
            self.opts.output = None
            
        [ pf.info(header["OPENNAME"], self.opts.output) for header in data.search(**search) ]
                

class FITSGroup(FITSCLI):
    """Create a list of groups from FITS header attributes."""
    
    command = 'group'
    
    help = "Make a list of groups for a collection of FITS files."
    
    description = fill("Creates a text table with the requested header information for a bunch of FITS files.")
        
    options = [ "i", "skw" ]        
        
    def do(self):
        """Make the log table"""
        files = self.get_files()
        search = self.get_keywords()
        print("Will group %d files." % len(files))
        data = FITSHeaderTable()
        data.read(files)
        output = data.search(**search).group(search.keys()).table()
        print("\n".join(output))
        print("%d files grouped." % len(data.collection))

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
        data = FITSHeaderTable()
        data.read(files)
        output = data.search(**search).normalize(search.keys()).logstring(order=search.keys())
        if self.opts.output:
            with open(self.opts.output,'w') as outputfile:
                outputfile.write("\n".join(output))
        else:
            print("\n".join(output))
            print("%d files found." % len(data.collection))
        
        
    
    
class FITSList(FITSCLI):
    """Make a list of files with certain header attributes"""
    
    command = "list"
    
    options = [ "i", "skw" ]
    
    help = "Make a list of FITS files that match criteria."
    
    description = "Make a list of FITS files that match given criteria using direct matching, substring matching, or regular expressions."
    
    def after_configure(self):
        super(FITSList, self).after_configure()
        self.parser.add_argument('-o','--output',action='store',
            default=self.config.get("Defaults.List.Name",False),help="Output file list name",metavar="files.list")
        self.parser.add_argument('-l','--log',action='store_true',
            help="Store a full log file, not just a list of files that match this keyword")
        
            
    def do(self):
        """Run the search itself"""
        search = self.get_keywords()
        files = self.get_files()
        print("Searching %d files." % len(files))
        data = FITSHeaderTable()
        data.read(files)
        output = data.normalize(search.keys()).search(**search).logstring(order=search.keys())
        print("\n".join(output))
        print("%d files found." % len(output))
        
        if self.opts.output:
            if not self.opts.log:
                output = data.search(**search).liststring()
            with open(self.opts.output,'w') as fnamelist:
                fnamelist.write("\n".join(output))
            print("Wrote file %s to '%s'" % ("log" if self.opts.log else "list",self.opts.output))
        
