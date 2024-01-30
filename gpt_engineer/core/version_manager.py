"""
Version Manager Module

This module provides an abstract base class for a version manager that handles the creation of snapshots
for code. Implementations of this class are expected to provide methods to create a snapshot of the given
code and return a reference to it.

Classes:
    BaseVersionManager: Abstract base class for a version manager.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from gpt_engineer.core.files_dict import FilesDict


class BaseVersionManager(ABC):
    """
    Abstract base class for a version manager.

    Defines the interface for version managers that handle the creation of snapshots for code.
    Implementations of this class are expected to provide methods to create a snapshot of the given
    code and return a reference to it.

    Methods
    -------
    __init__(self, path: Union[str, Path])
        Initializes the version manager with the given path.
    snapshot(self, files_dict: FilesDict) -> str
        Creates a snapshot of the given FilesDict object and returns a reference to it.
    """

    @abstractmethod
    def __init__(self, path: Union[str, Path]):
        pass

    @abstractmethod
    def snapshot(self, files_dict: FilesDict) -> str:
        pass
