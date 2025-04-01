__version__ = "1.5.0"

from .models import BookSearchResult, Category, DownloadFormat, BookDetails
from .exceptions import (
    ZLibraryException, NetworkError, ParsingError, SearchError,
    DetailFetchError, DownloadError, NoDownloadLinkError, RateLimitError,
    CacheLibNotFound
)
# Import Enums
from .enums import Language, Extension, OrderOptions
from .api import ZLibraryAPI

__all__ = [
    # Core API class
    "ZLibraryAPI",

    # Data Models
    "BookSearchResult",
    "Category",
    "DownloadFormat",
    "BookDetails",

    # Enums for Filtering/Ordering
    "Language",
    "Extension",
    "OrderOptions",

    # Exceptions
    "ZLibraryException",
    "NetworkError",
    "ParsingError",
    "SearchError",
    "DetailFetchError",
    "DownloadError",
    "NoDownloadLinkError",
    "RateLimitError",
    "CacheLibNotFound",

    # Metadata
    "__version__",
]