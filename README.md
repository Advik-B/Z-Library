# Z-Library API

[![PyPI version](https://badge.fury.io/py/zlibrary-sync.svg)](https://badge.fury.io/py/zlibrary-sync)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/pypi/pyversions/zlibrary-sync.svg)](https://pypi.org/project/zlibrary-sync/)

A **synchronous** Python library for interacting with the unofficial Z-Library web interface. It allows you to programmatically search for books, retrieve detailed information, and download files using standard blocking I/O operations.

---

**📌 Important Note:** This library is named `zlibrary-sync` on PyPI to clearly distinguish it from the excellent asynchronous [`zlibrary`](https://github.com/sertraline/zlibrary) library by sertraline. Choose `zlibrary-sync` if you need a simple, blocking library for scripts or applications where asynchronous operations are not required or desired.

---

**⚠️ Disclaimer:**
> This library interacts with Z-Library's web interface by scraping its pages. Z-Library's website structure can change at any time without notice, which **will break this library**. Use it at your own risk.
>
> This is an **unofficial** library and is not affiliated with, endorsed by, or supported by Z-Library.
---

## Features

*   📚 **Search Books:** Find books using queries and advanced filters:
    *   Order results (`popular`, `newest`, `relevance`, etc.)
    *   Exact title matching
    *   Filter by publication year range
    *   Filter by language(s) (using convenient `Language` Enum)
    *   Filter by file extension(s) (using convenient `Extension` Enum)
*   ℹ️ **Fetch Details:** Retrieve comprehensive book metadata:
    *   Title, Author(s), Author URL
    *   Description, Publisher, Year, Language, Series
    *   ISBN (10 & 13)
    *   File Format, File Size
    *   Cover Image URL
    *   Categories, Ratings
    *   IPFS CIDs (if available)
    *   Available download formats and links
*   💾 **Download Files:**
    *   Download books using the primary link or specify an alternative format URL.
    *   Includes a generator method (`download_with_progress`) for integrating with progress bars.
*   ⚡ **Disk Caching:**
    *   Automatically caches search results and book details using `diskcache` to speed up repeated requests and reduce load on the source.
    *   Caching is enabled by default but can be easily disabled or configured.
*   ✨ **Developer Friendly:**
    *   Simple, synchronous API.
    *   Provides Enums (`Language`, `Extension`, `OrderOptions`) for robust filtering.
    *   Type hinted for better code analysis and autocompletion.
    *   Custom exceptions for specific error conditions.

---

## Installation

Requires **Python 3.9+**.

```bash

pip install zlibrary-sync diskcache
```

*   `zlibrary-sync`: The core library.
*   `diskcache`: Required for the default caching functionality. If you disable caching (`use_cache=False`), `diskcache` is not strictly needed, but it's recommended for typical usage.

---

## Usage Examples

**Important:** The package is installed as `zlibrary-sync`, but you import it in your Python code as `zlibrary_api`.

```python
# Import necessary components
import os
from zlibrary import (
    ZLibraryAPI,
    ZLibraryException,    # Base exception
    BookDetails,
    NoDownloadLinkError,  # Specific exception
    Language,             # Enum for languages
    Extension,            # Enum for file extensions
    OrderOptions          # Enum for search order
)

# --- Initialization ---
# Caching is enabled by default in '.zlib_cache' directory
# api = ZLibraryAPI()

# Disable caching:
# api = ZLibraryAPI(use_cache=False)

# Use a custom cache directory and expiry (1 hour):
# api = ZLibraryAPI(cache_dir='/tmp/my_zlib_cache', cache_expire=3600)

# Use a specific Z-Library mirror:
# api = ZLibraryAPI(base_url="https://your-mirror-domain.org")

api = ZLibraryAPI() # Use defaults for this example

# --- Example 1: Search and Get Details ---
try:
    print("Searching for popular Python books (EPUB/PDF)...")
    search_results = api.search(
        query="Python Programming",
        order=OrderOptions.POPULAR,
        languages=[Language.ENGLISH],
        extensions=[Extension.EPUB, Extension.PDF] # Pass a list of enums
        # Alternatively, use strings: extensions=['epub', 'pdf']
    )

    if not search_results:
        print("No matching books found.")
    else:
        print(f"Found {len(search_results)} results. Details for the first:")
        first_book = search_results[0]
        print(f"  Title: {first_book.title}")
        print(f"  URL: {first_book.url}")

        # Fetch detailed info (this might hit the cache if run before)
        details: BookDetails = api.get_book_details(first_book.url)

        print(f"  Author: {details.author}")
        print(f"  Year: {details.year}")
        print(f"  Format: {details.file_format}")
        print(f"  Size: {details.file_size}")
        print(f"  ISBN-13: {details.isbn_13}")
        # print(f"  Description: {details.description[:150]}...") # Uncomment for snippet

except ZLibraryException as e:
    print(f"An API error occurred during search/detail fetch: {e}")
except ValueError as e: # Handles invalid enum strings if passed directly
    print(f"Invalid parameter error: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")


# --- Example 2: Finding a Download Link and Downloading ---
if 'details' in locals() and details: # Check if details were fetched successfully
    print("\nAttempting to find a download link...")

    # Prefer direct download URL, fallback to first available alternative
    target_url = None
    target_format = None

    if details.download_url and details.download_url != 'CONVERSION_NEEDED':
        target_url = details.download_url
        target_format = details.file_format or 'primary'
        print(f"  Using primary download link ({target_format}).")
    else:
        print("  Primary link requires conversion or is missing. Checking alternatives...")
        for fmt in details.other_formats:
            if fmt.url and fmt.url != 'CONVERSION_NEEDED':
                target_url = fmt.url
                target_format = fmt.format
                print(f"  Found alternative link: {target_format}")
                break # Use the first valid alternative

    if target_url:
        try:
            download_dir = "downloaded_books"
            print(f"\nDownloading '{details.title}' ({target_format}) to '{download_dir}/'...")

            # Option A: Simple Download
            # filepath = api.download(details, download_url=target_url, download_dir=download_dir)
            # print(f"Download complete: {filepath}")

            # Option B: Download with Progress Updates
            generator = api.download_with_progress(
                details,
                download_url=target_url,
                download_dir=download_dir,
                overwrite=False # Set to True to overwrite existing files
            )
            final_filepath = None
            for current_bytes, total_bytes, status_msg in generator:
                 status, _, msg = status_msg.partition(': ')
                 total_str = f"{(total_bytes or 0) / (1024*1024):.2f} MB" if total_bytes else "?"
                 current_str = f"{current_bytes / (1024*1024):.2f}"

                 print(f"\r  -> Status: {status:<12} | Progress: {current_str} / {total_str} MB   ", end="")

                 if status == 'completed':
                      final_filepath = msg # Filepath is in msg on completion
                 elif status == 'error':
                      print(f"\nDownload Error Message: {msg}")
                      break # Exit loop on error

            print() # Newline after progress bar
            if final_filepath:
                  print(f"Download complete: {final_filepath}")

        except NoDownloadLinkError:
            # This shouldn't happen if target_url was found, but good practice
            print("Error: No valid download URL could be determined.")
        except ZLibraryException as e:
            print(f"\nAn error occurred during download: {e}")
        except Exception as e:
            print(f"\nAn unexpected error occurred during download: {e}")

    else:
        print("Could not find any direct download link (primary or alternative).")
        print("Conversion might be required via the website, or the book may not be available for direct download.")

# --- Optional: Clear Cache ---
# try:
#     cleared_count = api.clear_cache()
#     print(f"\nCache cleared. Removed {cleared_count} items.")
# except ZLibraryException as e:
#     print(f"\nError clearing cache: {e}")

```

---

## Caching

*   By default, `zlibrary-sync` uses `diskcache` to cache the results of `search()` and `get_book_details()` calls in a local directory (`.zlib_cache` relative to where your script runs).
*   This significantly speeds up repeated requests for the same data and reduces the number of requests made to Z-Library.
*   **Disable Caching:** `api = ZLibraryAPI(use_cache=False)`
*   **Change Cache Directory:** `api = ZLibraryAPI(cache_dir="/path/to/your/cache")`
*   **Change Cache Expiry:** `api = ZLibraryAPI(cache_expire=3600)` (seconds, None for indefinite)
*   **Clear Cache:** `api.clear_cache()`

---

## Error Handling

The library defines several custom exceptions inheriting from `ZLibraryException`:

*   `NetworkError`: General connection, timeout, or HTTP errors.
*   `RateLimitError`: Suspected rate limiting, login, or CAPTCHA pages encountered.
*   `ParsingError`: Failed to parse expected data from the page HTML.
*   `SearchError`, `DetailFetchError`: Errors specific to those operations.
*   `DownloadError`: Errors during the file writing process.
*   `NoDownloadLinkError`: Could not find a usable direct download URL.
*   `CacheLibNotFound`: `use_cache=True` but `diskcache` is not installed.

It's recommended to wrap API calls in a `try...except ZLibraryException as e:` block to catch library-specific issues. You can also catch more specific exceptions if needed.

---

## API Reference

Currently, the best reference is the source code itself, which includes type hints and docstrings explaining the parameters and return types for methods like `search()`, `get_book_details()`, `download()`, and `download_with_progress()`.

---

## Contributing

Contributions, bug reports, and feature requests are welcome! Please feel free to open an issue or submit a pull request on the [project repository](https://github.com/Advik-B/z-library).

---

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.
