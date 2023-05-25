"""
Rebiber: A tool for normalizing bibtex with official info.
"""

from rebiber.bib2json import load_bib_file
from rebiber.normalize import construct_bib_db, normalize_bib

__version__ = "1.1.3"

__all__ = ["__version__", "load_bib_file", "construct_bib_db", "normalize_bib"]
