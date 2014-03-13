# -*- coding: utf-8 -*-
# 
#  core.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-04.
#  Copyright 2014 University of California. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)


from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import validates, relationship, backref
from sqlalchemy.ext.declarative import declarative_base, declared_attr

Base = declarative_base()

class DataBase(Base):
    """A mixin class for nebulous SQLAlchemy objects."""
    
    __abstract__ = True
    
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()
    
    id =  Column(Integer, primary_key=True)
    
    def as_dictionary(self):
        """Return the item as a dictionary."""
        return { column.name : getattr(self, column.name) for column in self.__table__.columns }
        
    def as_serializable_dictionary(self):
        """Return a serializable dictionary, handling special column types (quantities with units.)."""
        s_dict = dict()
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            value = getattr(column.type, 'serialize', lambda x : x)(value)
            s_dict[column.name] = value
        return s_dict
        
    @classmethod
    def from_serializeable_dictionary(cls, s_dict):
        """Return an object created from a serialized dictionary."""
        columns = { column.name:column for column in cls.__table__.columns }
        kwargs = dict()
        for key in s_dict.keys():
            column = columns[key]
            kwargs[key] = getattr(column.type, 'deserialize', lambda x : x)(s_dict[key])
        return cls(**kwargs)


class SubDataBase(DataBase):
    """A class for things which belong to a master class."""
    
    __abstract__ = True
    __master_class__ = None
    
    @declared_attr
    def master_id(cls):
        """Return the master ID column."""
        return Column(Integer, ForeignKey(cls.__master_class__.__tablename__ + '.id'))
        
    @declared_attr
    def master(self):
        """Build the master relationship."""
        return relationship(cls.__master_class__.__name__)
        
