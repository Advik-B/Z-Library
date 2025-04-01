# zlibrary_api/exceptions.py
# -*- coding: utf-8 -*-

class ZLibraryException(Exception):
    """Base exception for the zlibrary_api library."""
    pass

class NetworkError(ZLibraryException):
    """Raised for network-related issues (timeouts, connection errors, HTTP errors)."""
    pass

class ParsingError(ZLibraryException):
    """Raised when HTML parsing fails or expected elements are missing."""
    pass

class SearchError(ZLibraryException):
    """Raised for errors specifically during the search process."""
    pass

class DetailFetchError(ZLibraryException):
    """Raised for errors specifically during the detail fetching process."""
    pass

class DownloadError(ZLibraryException):
    """Raised for errors during the file download process (after request succeeded)."""
    pass

class NoDownloadLinkError(DownloadError):
    """Raised when no suitable direct download link is found or provided."""
    pass

class RateLimitError(NetworkError):
    """Raised when a rate limit, login, or CAPTCHA page is suspected."""
    pass

class CacheLibNotFound(ZLibraryException):
    """Raised when the caching library (diskcache) is not installed but caching is enabled."""
    pass