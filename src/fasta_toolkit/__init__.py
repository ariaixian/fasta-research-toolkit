"""Privacy-conscious utilities for reproducible FASTA file preparation."""

from .models import FastaRecord
from .parser import FastaFormatError, parse_fasta, write_fasta

__all__ = ["FastaFormatError", "FastaRecord", "parse_fasta", "write_fasta"]
__version__ = "0.2.0"
