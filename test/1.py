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
        query="Python",
        # languages=[Language.ENGLISH],
        # extensions=[Extension.PDF] # Pass a list of enums
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
        print(f"  Download Link: {details.download_url}")

except ZLibraryException as e:
    print(f"An API error occurred during search/detail fetch: {e}")
except ValueError as e: # Handles invalid enum strings if passed directly
    print(f"Invalid parameter error: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")