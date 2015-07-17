"""
Base classes.
"""

from abc import ABCMeta, abstractmethod

# Base Classes


class Persist():

    """
    Persist is an Abstract class-interface
    Classes extending/implementing Persist are expected to implement:
    load() - Re-define the ESH objects from data found in the CORE database
    save() - Convert the ESH objects into CORE database objects
    delete() - Remove the CORE database object corresponding to the ESH object
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def load(self):
        """
        load() - Re-define the ESH objects from data found in the CORE database
        """
        raise NotImplemented

    @abstractmethod
    def save(self):
        """
        save() - Convert the ESH objects into CORE database objects
        """
        raise NotImplemented

    @abstractmethod
    def delete(self):
        """
        delete() - Remove the CORE database object matching the ESH object
        """
        raise NotImplemented
