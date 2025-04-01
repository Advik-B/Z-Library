# zlibrary_api/models.py
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from typing import Optional, List

# Note: These models are used for type hinting and structuring data.
# They are also stored directly in the cache.

@dataclass
class BookSearchResult:
    """Represents a single book result from a search."""
    title: str
    url: str
    book_id: Optional[str] = None

@dataclass
class Category:
    """Represents a book category with name and URL."""
    name: str
    url: Optional[str] = None

@dataclass
class DownloadFormat:
    """Represents an available download format and its URL."""
    format: str
    url: str # Can be direct URL or 'CONVERSION_NEEDED'

@dataclass
class BookDetails:
    """Represents the detailed information for a single book."""
    # Core Identifiers
    url: str
    book_id: Optional[str] = None

    # Primary Metadata
    title: Optional[str] = None
    author: Optional[str] = None
    author_url: Optional[str] = None
    description: Optional[str] = None
    year: Optional[str] = None
    publisher: Optional[str] = None
    language: Optional[str] = None
    series: Optional[str] = None

    # File Details (Primary Download)
    file_format: Optional[str] = None
    file_size: Optional[str] = None
    download_url: Optional[str] = None # Primary direct download URL or CONVERSION_NEEDED

    # Other Details
    isbn_10: Optional[str] = None
    isbn_13: Optional[str] = None
    categories: List[Category] = field(default_factory=list)
    cover_url: Optional[str] = None
    rating_interest: Optional[str] = None
    rating_quality: Optional[str] = None
    content_type: Optional[str] = None # E.g., 'book', 'article' if available
    volume: Optional[str] = None # If part of a volume

    # Technical Details
    ipfs_cid: Optional[str] = None
    ipfs_cid_blake2b: Optional[str] = None

    # Other Available Formats/Links
    other_formats: List[DownloadFormat] = field(default_factory=list)