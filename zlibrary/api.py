# zlibrary_api/api.py
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import os
import json
from enum import Enum  # Needed for isinstance check
# Import Union for type hints
from typing import Optional, List, Dict, Any, Generator, Tuple, Union

# Conditional import for diskcache
try:
    from diskcache import Cache as DiskCache

    DISKCACHE_AVAILABLE = True
except ImportError:
    DISKCACHE_AVAILABLE = False
    DiskCache = None  # Define it as None if not available

from .models import BookSearchResult, Category, DownloadFormat, BookDetails
from .exceptions import (
    ZLibraryException, NetworkError, ParsingError, SearchError,
    DetailFetchError, DownloadError, NoDownloadLinkError, RateLimitError,
    CacheLibNotFound
)
# Import Enums
from .enums import Language, Extension, OrderOptions
from .utils import DEFAULT_BASE_URL, SEARCH_PATH, create_session, sanitize_filename


class ZLibraryAPI:
    """
    A synchronous client for interacting with Z-Library's unofficial web interface.

    Handles searching, fetching book details, and downloading.
    Manages a persistent requests session and optional disk caching.
    """

    def __init__(self,
                 base_url: str = DEFAULT_BASE_URL,
                 session: Optional[requests.Session] = None,
                 use_cache: bool = True,
                 cache_dir: str = ".zlibrary_cache",
                 cache_expire: Optional[int] = 3600 * 24  # Cache expiry in seconds (default: 1 day)
                 ):
        """
        Initializes the ZLibraryAPI client.

        Args:
            base_url: The base URL of the Z-Library instance.
            session: An optional pre-configured requests.Session object.
                     If None, a new session will be created.
            use_cache: Enable or disable caching of search results and book details.
            cache_dir: Directory to store cache files.
            cache_expire: Default cache expiry time in seconds (None for no expiry).
        """
        self.base_url = base_url.rstrip('/')
        self.session = session if session else create_session(self.base_url)
        self.use_cache = use_cache
        self.cache_expire = cache_expire
        self.cache: Optional[DiskCache] = None  # Type hint for the cache object

        if self.use_cache:
            if not DISKCACHE_AVAILABLE:
                raise CacheLibNotFound(
                    "'diskcache' library not found but use_cache=True. "
                    "Install it (`pip install diskcache`) or set use_cache=False."
                )
            # Ensure cache directory exists (diskcache might do this, but doesn't hurt)
            os.makedirs(cache_dir, exist_ok=True)
            self.cache = DiskCache(cache_dir)

    def get_session(self) -> requests.Session:
        """Returns the managed requests session."""
        return self.session

    def clear_cache(self) -> int:
        """Clears the entire disk cache if caching is enabled. Returns number of items cleared."""
        if self.use_cache and self.cache:
            count = self.cache.clear()
            return count
        return 0

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Makes an HTTP request using the managed session. (Caching is NOT done here)"""
        try:
            kwargs.setdefault('timeout', 30)
            absolute_url = urljoin(self.base_url, url)  # Ensure URL is absolute for the request
            response = self.session.request(method, absolute_url, **kwargs)
            self.session.headers.update({'Referer': response.url})
            content_type = response.headers.get('content-type', '').lower()

            if response.status_code == 200 and 'text/html' in content_type and not kwargs.get('stream', False):
                soup_check = BeautifulSoup(response.text, 'html.parser')
                if soup_check.find('form', action=re.compile(r'/login')):
                    raise RateLimitError(
                        f"Detected possible login page at {response.url}. Status: {response.status_code}")
                if soup_check.find('div', class_='g-recaptcha'):
                    raise RateLimitError(
                        f"Detected possible CAPTCHA page at {response.url}. Status: {response.status_code}")

            response.raise_for_status()
            return response
        except requests.exceptions.Timeout as e:
            raise NetworkError(f"Request timed out for {url}: {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"Connection error for {url}: {e}") from e
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else 'Unknown'
            raise NetworkError(f"HTTP error {status_code} for {url}: {e}") from e
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Request failed for {url}: {e}") from e

    def _generate_search_cache_key(self, query: str, **kwargs) -> str:
        """Generates a stable cache key for search parameters."""
        params = {'q': query}
        params.update({k: v for k, v in kwargs.items() if v is not None})  # Filter None

        normalized_params = {}
        for k, v in sorted(params.items()):
            if isinstance(v, (Language, Extension, OrderOptions)):
                normalized_params[k] = v.value
            elif isinstance(v, list):
                normalized_params[k] = sorted([item.value if isinstance(item, Enum) else str(item) for item in v])
            elif isinstance(v, bool):
                normalized_params[k] = '1' if v else '0'
            else:
                normalized_params[k] = str(v)

        key_data = json.dumps(normalized_params, sort_keys=True)
        return f"search:{key_data}"

    def search(self,
               query: str,
               order: Optional[OrderOptions] = None,
               exact_match: bool = False,
               year_from: Optional[int] = None,
               year_to: Optional[int] = None,
               languages: Optional[List[Union[Language, str]]] = None,
               extensions: Optional[List[Union[Extension, str]]] = None,
               content_types: Optional[List[str]] = None
               ) -> List[BookSearchResult]:
        """
        Searches Z-Library for books, using cache if enabled.

        Args:
            query: The search term.
            order: The order of search results (e.g., OrderOptions.POPULAR).
            exact_match: Whether to search for an exact match.
            year_from: Starting year for filtering.
            year_to: Ending year for filtering.
            languages: List of languages (use Language Enum or string codes).
            extensions: List of file extensions (use Extension Enum or string codes).
            content_types: List of content types (e.g., ['book', 'article']).

        Returns:
            A list of BookSearchResult objects.

        Raises:
            SearchError: If the search request or parsing fails.
            NetworkError: For network-related issues.
            RateLimitError: If a login/captcha page is detected.
            CacheLibNotFound: If caching is enabled but diskcache isn't installed.
            ValueError: If invalid Enum strings are passed in lists.
        """
        cache_key = None
        # Process list arguments to ensure they are strings (enum values)
        lang_values: Optional[List[str]] = None
        if languages:
            lang_values = []
            for lang in languages:
                if isinstance(lang, Language):
                    lang_values.append(lang.value)
                elif isinstance(lang, str):
                    try:
                        Language(lang.lower());
                        lang_values.append(lang.lower())
                    except ValueError:
                        raise ValueError(f"Invalid language string: '{lang}'")
                else:
                    raise TypeError("languages list must contain Language enums or string codes.")

        ext_values: Optional[List[str]] = None
        if extensions:
            ext_values = []
            for ext in extensions:
                if isinstance(ext, Extension):
                    ext_values.append(ext.value)
                elif isinstance(ext, str):
                    try:
                        Extension(ext.lower());
                        ext_values.append(ext.lower())
                    except ValueError:
                        raise ValueError(f"Invalid extension string: '{ext}'")
                else:
                    raise TypeError("extensions list must contain Extension enums or string codes.")

        # Generate cache key using processed values
        if self.use_cache and self.cache:
            search_params_filtered = {k: v for k, v in {
                'order': order, 'exact_match': exact_match, 'year_from': year_from, 'year_to': year_to,
                'languages': lang_values, 'extensions': ext_values, 'content_types': content_types
            }.items() if v is not None}
            cache_key = self._generate_search_cache_key(query, **search_params_filtered)
            cached_result = self.cache.get(cache_key)
            if cached_result is not None: return cached_result  # Return cached data directly

        # Cache Miss or Cache Disabled
        search_url = urljoin(self.base_url, SEARCH_PATH)
        params: Dict[str, Any] = {'q': query}
        if order: params['order'] = order.value
        if exact_match: params['e'] = '1'
        if year_from: params['yearFrom'] = str(year_from)
        if year_to: params['yearTo'] = str(year_to)
        if lang_values: params['languages[]'] = lang_values  # Use processed string list
        if ext_values: params['extensions[]'] = ext_values  # Use processed string list
        if content_types: params['content_types[]'] = content_types  # Assuming this is still string list

        try:
            # Use url directly as _make_request handles joining with base_url
            response = self._make_request('GET', SEARCH_PATH, params=params)
            soup = BeautifulSoup(response.text, 'html.parser')
            results_list: List[BookSearchResult] = []
            result_items = soup.select('div#searchResultBox div.book-item, div#searchResultBox div.resItemBoxBooks')

            if not result_items and ("No books found" in response.text or "nothing was found" in response.text.lower()):
                if self.use_cache and self.cache and cache_key: self.cache.set(cache_key, [], expire=self.cache_expire)
                return []

            for item in result_items:
                book_card = item.find('z-bookcard')
                if book_card:
                    relative_url = book_card.get('href')
                    book_id_attr = book_card.get('id') or book_card.get('data-bookid')
                    book_id = None
                    if book_id_attr and 'book' in book_id_attr.lower():
                        match = re.search(r'(\d+)', book_id_attr);
                        book_id = match.group(1) if match else None
                    title_slot = book_card.find('div', slot='title')
                    title = title_slot.get_text(strip=True) if title_slot else "Title N/A"
                    if relative_url:
                        full_url = urljoin(self.base_url, relative_url)
                        if not book_id: match = re.search(r'/book/(\d+)', full_url); book_id = match.group(
                            1) if match else None
                        results_list.append(BookSearchResult(title=title, url=full_url, book_id=book_id))
                else:  # Fallback parsing
                    header = item.find('h3', class_='itemHeader')
                    title_link = header.find('a', href=re.compile(r'/book/')) if header else None
                    if not title_link: title_link = item.select_one('div.itemCover a[href*="/book/"]')
                    if title_link:
                        title_text = title_link.get_text(strip=True)
                        if not title_text: inner_title = title_link.find(
                            ['b', 'strong', 'span']); title_text = inner_title.get_text(
                            strip=True) if inner_title else None
                        title = title_text if title_text else "Title N/A"
                        relative_url = title_link['href']
                        full_url = urljoin(self.base_url, relative_url)
                        match = re.search(r'/book/(\d+)', full_url);
                        book_id = match.group(1) if match else None
                        results_list.append(BookSearchResult(title=title, url=full_url, book_id=book_id))

            if self.use_cache and self.cache and cache_key: self.cache.set(cache_key, results_list,
                                                                           expire=self.cache_expire)
            return results_list

        except RateLimitError as e:
            raise SearchError(f"Search failed due to potential rate limit/login requirement: {e}") from e
        except NetworkError as e:
            raise SearchError(f"Network error during search: {e}") from e
        except ValueError as e:
            raise SearchError(f"Invalid search parameter: {e}") from e  # Catch enum validation errors
        except Exception as e:
            # Use response.url if available for better error reporting
            url_for_error = response.url if 'response' in locals() and hasattr(response, 'url') else search_url
            raise ParsingError(f"Failed to parse search results page {url_for_error}: {e}") from e

    def get_book_details(self, book_url: str) -> BookDetails:
        """
        Fetches and parses detailed information for a specific book URL, using cache if enabled.

        Args:
            book_url: The full URL of the book's detail page.

        Returns:
            A BookDetails object.

        Raises:
            DetailFetchError: If fetching or parsing fails.
            NetworkError: For network-related issues.
            RateLimitError: If a login/captcha page is detected.
            CacheLibNotFound: If caching is enabled but diskcache isn't installed.
            ParsingError: If the page structure cannot be parsed.
        """
        cache_key = f"details:{book_url}"

        if self.use_cache and self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result is not None and isinstance(cached_result, BookDetails):
                return cached_result

        try:
            response = self._make_request('GET', book_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            data_dict: Dict[str, Any] = {}

            # --- Extract Details (Most logic remains the same) ---
            book_id_match = re.search(r'/book/(\d+)', book_url)
            data_dict['book_id'] = book_id_match.group(1) if book_id_match else None
            # ... (Title, Author, Description, Ratings, Properties Box, Cover Image logic remains the same as before) ...
            # --- Start of existing parsing logic ---
            title_tag = soup.find('h1', itemprop='name') or soup.find('h1', class_='book-title');
            data_dict['title'] = title_tag.get_text(strip=True) if title_tag else "Title N/A"
            main_content = soup.find('div', class_='book-details-container') or soup

            # Author parsing
            author_container = main_content.find('div', class_='book-details-property-author');
            author_tag = None
            if author_container: author_tag = author_container.find('a', href=re.compile(r'/g/|/authors/'))
            if not author_tag: author_tag = main_content.find('a', itemprop='author', href=re.compile(r'/g/|/authors/'))
            if not author_tag: author_tag = main_content.find(string=re.compile(r'\bAuthor(s)?:\b', re.I))
            if author_tag:
                author_parent = author_tag.find_parent();
                author_link = author_parent.find('a', href=re.compile(r'/g/|/authors/')) if author_parent else None
                if author_link:
                    data_dict['author'] = author_link.get_text(strip=True);
                    href = author_link.get('href')
                    if href: data_dict['author_url'] = urljoin(self.base_url, href)
                elif author_parent:
                    value_tag = author_parent.find(class_=re.compile(r'property[_-]value', re.I));
                    data_dict[
                        'author'] = value_tag.get_text(strip=True) if value_tag else None

            # Description
            desc_tag = main_content.find('div', itemprop='description') or main_content.find('div',
                                                                                             id='bookDescriptionBox') or main_content.find(
                'div', class_='description-box')
            data_dict['description'] = desc_tag.get_text(strip=True) if desc_tag else None

            # Ratings
            rating_interest_tag = soup.find(class_='book-rating-interest-score');
            data_dict['rating_interest'] = rating_interest_tag.get_text(strip=True) if rating_interest_tag else None
            rating_quality_tag = soup.find(class_='book-rating-quality-score');
            data_dict['rating_quality'] = rating_quality_tag.get_text(strip=True) if rating_quality_tag else None

            # Properties Box
            categories_list: List[Category] = [];
            prop_container = soup.find('div', class_='book-details-properties') or soup
            prop_tags = prop_container.select('.properties .property, .bookProperty, .property-row')

            for tag in prop_tags:
                label_tag = tag.find(class_=re.compile(r'property[_-]label', re.I)) or tag.find('dt')
                value_tag = tag.find(class_=re.compile(r'property[_-]value', re.I)) or tag.find('dd')
                if label_tag and value_tag:
                    label_raw = label_tag.get_text(strip=True).lower();
                    label = re.sub(r':$', '', label_raw).replace(' ', '_')
                    value_text = value_tag.get_text(strip=True);
                    value_html = value_tag
                    if not value_text and not list(value_html.children): continue

                    if 'categor' in label:
                        for link in value_html.find_all('a', href=re.compile(r'/category/|/schema/')):
                            cat_name = link.get_text(strip=True);
                            href = link.get('href')
                            cat_url = urljoin(self.base_url, href) if href else None
                            if cat_name: categories_list.append(Category(name=cat_name, url=cat_url))
                    elif 'file' == label or ('size' in label and 'format' in label):
                        parts = [p.strip() for p in value_text.split(',')];
                        if len(parts) > 0 and parts[0]: data_dict.setdefault('file_format', parts[0].lower())
                        if len(parts) > 1 and parts[1]: data_dict.setdefault('file_size', parts[1])
                    elif 'ipfs' == label:
                        cids = value_html.select('span[data-copy]')
                        if len(cids) > 0: data_dict['ipfs_cid'] = cids[0]['data-copy']
                        if len(cids) > 1: data_dict['ipfs_cid_blake2b'] = cids[1]['data-copy']
                    elif 'isbn' == label:
                        for isbn_val in [isbn.strip() for isbn in value_text.split(',')]:
                            cleaned_isbn = isbn_val.replace('-', '').replace(' ', '')
                            if len(cleaned_isbn) == 10 and 'isbn_10' not in data_dict: data_dict['isbn_10'] = isbn_val
                            if len(cleaned_isbn) == 13 and 'isbn_13' not in data_dict: data_dict['isbn_13'] = isbn_val
                    elif label in BookDetails.__annotations__:
                        if value_text: data_dict.setdefault(label, value_text)
            data_dict['categories'] = categories_list

            # Cover Image
            cover_tag = soup.find('img', class_='book-cover-image') or soup.find('img', itemprop='image')
            if not cover_tag: cover_z_tag = soup.find('z-cover'); cover_tag = cover_z_tag.find(
                'img') if cover_z_tag else None
            if cover_tag:
                src_attr = cover_tag.get('data-src') or cover_tag.get('src')
                if src_attr:
                    if '/covers100/' in src_attr:
                        src_attr = src_attr.replace('/covers100/', '/covers210/')
                    elif '/covers/s/' in src_attr:
                        src_attr = src_attr.replace('/covers/s/', '/covers/l/')
                    elif '/small/' in src_attr:
                        src_attr = src_attr.replace('/small/', '/medium/')
                    data_dict['cover_url'] = urljoin(self.base_url, src_attr)
            # --- End of unchanged parsing logic ---

            # --- Download Links (REVISED SECTION) ---
            # Find the container for download buttons more specifically
            dl_container = soup.select_one('div.details-buttons-container') or soup.select_one(
                '.book-actions-buttons') or soup

            # Look specifically for the download button using addDownloadedBook class and /dl/ href
            primary_dl_link = dl_container.select_one('a.addDownloadedBook[href*="/dl/"]')

            if primary_dl_link and primary_dl_link.get('href'):
                href = primary_dl_link['href']
                # Ensure the href is definitely a download link (contains /dl/)
                if '/dl/' in href:
                    data_dict['download_url'] = urljoin(self.base_url, href)
                    button_text = primary_dl_link.get_text(" ", strip=True)

                    # Extract format/size if not already found in properties
                    if 'file_format' not in data_dict:
                        # Try specific span first
                        fmt_tag = primary_dl_link.find('span', class_='book-property__extension')
                        if fmt_tag:
                            data_dict['file_format'] = fmt_tag.get_text(strip=True).lower()
                        else:  # Fallback to parsing text like (pdf, 1.25 MB)
                            fmt_match = re.search(r'\(([^,]+),', button_text)
                            if fmt_match: data_dict['file_format'] = fmt_match.group(1).strip().lower()

                    if 'file_size' not in data_dict:
                        size_match = re.search(r'(\d+(\.\d+)?\s*(KB|MB|GB))', button_text, re.I)
                        if size_match: data_dict['file_size'] = size_match.group(1)
                # else:
                #     print(f"DEBUG: Found addDownloadedBook link, but href '{href}' doesn't contain '/dl/'. Skipping.")

            # --- Other Formats / Conversion (Keep existing logic) ---
            other_formats_list: List[DownloadFormat] = []
            formats_container = soup.select_one('.book-details-downloads-container, #bookOtherFormatsContainer')
            if formats_container:
                # Direct download links for other formats
                format_links = formats_container.select('a[href*="/dl/"]')  # Simpler selector for alternatives
                for link in format_links:
                    href = link.get('href')
                    if href:
                        format_str = "unknown"
                        format_tag = link.find(['span', 'div'], class_=re.compile(r'extension|format', re.I))
                        if format_tag:
                            format_str = format_tag.get_text(strip=True).lower()
                        else:
                            link_text = link.get_text(" ", strip=True);
                            fmt_match = re.search(r'\(([^,]+),',
                                                  link_text);
                            format_str = fmt_match.group(
                                1).strip().lower() if fmt_match else link_text.split(' ')[0].lower()
                        other_formats_list.append(DownloadFormat(format=format_str, url=urljoin(self.base_url, href)))

                # Conversion links
                converter_links = formats_container.select('a[data-convert_to]')
                for link in converter_links:
                    convert_to = link.get('data-convert_to')
                    if convert_to: other_formats_list.append(
                        DownloadFormat(format=convert_to.lower(), url='CONVERSION_NEEDED'))
            data_dict['other_formats'] = other_formats_list
            # --- End of Other Formats logic ---

            # Construct final object
            valid_keys = BookDetails.__annotations__.keys()
            filtered_data = {k: v for k, v in data_dict.items() if k in valid_keys}
            book_details_obj = BookDetails(url=book_url, **filtered_data)

            # Cache the successful result
            if self.use_cache and self.cache:
                self.cache.set(cache_key, book_details_obj, expire=self.cache_expire)

            return book_details_obj

        # --- Error Handling (Remains the same) ---
        except RateLimitError as e:
            raise DetailFetchError(f"Fetching details failed: {e}") from e
        except NetworkError as e:
            raise DetailFetchError(f"Network error fetching details for {book_url}: {e}") from e
        except Exception as e:
            raise ParsingError(f"Failed to parse details page {book_url}: {e}") from e

    def _check_response_content_type(self, response: requests.Response, url: str):
        """Check if the response content type is valid for a file download."""
        content_type = response.headers.get('content-type', '').lower()
        # Allow octet-stream and common file types, block HTML/JSON etc.
        if any(ct in content_type for ct in ['text/html', 'text/plain', 'application/json']):
            try:
                # Peek at the beginning of the content without consuming much
                preview = next(response.iter_content(chunk_size=512, decode_unicode=True)).lstrip()
                # Check for common HTML/JSON patterns
                if re.match(r'<(!doctype|html|head|body)|^\s*\{|^\s*\[', preview, re.I):
                    raise RateLimitError(
                        f"Download failed: Received non-file content (likely HTML/JSON) from {url}. Content-Type: {content_type}")
            except StopIteration:  # Empty response
                raise DownloadError(f"Download failed: Empty response from {url}")
            except UnicodeDecodeError:
                pass  # Probably binary data, which is good
            except RateLimitError:
                raise  # Re-raise the specific error
            except Exception:
                pass  # Proceed cautiously if peeking failed for other reasons

    def _prepare_download_target(self, details: BookDetails, download_url: Optional[str],
                                 download_dir: str, filename: Optional[str]) -> Tuple[str, str]:
        """
        Helper method to determine the final download URL, construct the target filepath,
        and create the download directory.

        Args:
            details: The BookDetails object.
            download_url: Optional specific download URL (relative or absolute).
            download_dir: The target directory for the download.
            filename: Optional desired filename (without extension).

        Returns:
            A tuple containing:
                - filepath (str): The absolute path for the file to be saved.
                - final_url_to_download (str): The relative or absolute URL determined for download.

        Raises:
            NoDownloadLinkError: If no suitable download URL can be found or if conversion is needed.
        """
        final_url_to_download = download_url or details.download_url
        if not final_url_to_download:
            raise NoDownloadLinkError("No download URL specified or found in book details.")
        # Explicitly check for conversion placeholder
        if final_url_to_download == 'CONVERSION_NEEDED':
            raise NoDownloadLinkError(
                f"Download URL '{final_url_to_download}' requires conversion, which is not supported directly.")

        # Ensure the download directory exists
        os.makedirs(download_dir, exist_ok=True)

        # Determine base filename (without extension)
        if filename:
            base_filename = sanitize_filename(filename)
        else:
            # Construct a filename from book details
            title_part = details.title or f"book_{details.book_id}" if details.book_id else "Unknown_Book"
            author_part = details.author or "Unknown_Author"
            # Sanitize parts individually before combining
            base_filename = sanitize_filename(f"{sanitize_filename(author_part)} - {sanitize_filename(title_part)}")

        # Determine file extension
        file_extension = None
        # Make the target URL absolute for comparison if it's relative
        absolute_target_url = urljoin(self.base_url, final_url_to_download)

        # Check if the chosen URL matches one of the 'other_formats' to get the extension
        for fmt in details.other_formats:
            if fmt.url and fmt.url != 'CONVERSION_NEEDED':
                absolute_fmt_url = urljoin(self.base_url, fmt.url)
                if absolute_fmt_url == absolute_target_url:
                    file_extension = fmt.format.lower()
                    break  # Found matching format

        # If not found in other_formats, use the primary file_format if the primary download URL was chosen
        if not file_extension and (not download_url or urljoin(self.base_url, download_url) == urljoin(self.base_url,
                                                                                                       details.download_url)):
            file_extension = (details.file_format or 'file').lower()

        # Fallback if extension still not determined (e.g., custom URL provided with no match)
        if not file_extension:
            # Try to guess from the URL path itself
            path_part = urlparse(final_url_to_download).path
            if '.' in os.path.basename(path_part):
                file_extension = os.path.basename(path_part).split('.')[-1].lower()
            else:
                file_extension = 'file'  # Ultimate fallback

        # Clean up the determined extension
        file_extension = file_extension.lstrip('.').strip()
        # Basic validation for extension format
        if not file_extension or not re.match(r'^[a-z0-9\+]+$', file_extension) or len(file_extension) > 10:
            file_extension = 'file'  # Reset to default if invalid

        # Construct the full file path
        filepath = os.path.join(download_dir, f"{base_filename}.{file_extension}")

        return filepath, final_url_to_download

    def download(self, details: BookDetails, download_url: Optional[str] = None,
                 download_dir: str = "downloads", filename: Optional[str] = None,
                 overwrite: bool = False) -> str:
        """
        Downloads a book file. (Does NOT cache download stream).

        Args:
            details: BookDetails object containing book metadata.
            download_url: Optional specific download URL (relative or absolute).
                          If None, uses details.download_url.
            download_dir: Directory to save the downloaded file.
            filename: Optional filename (without extension). If None, generated from details.
            overwrite: If True, overwrite existing file. Defaults to False.

        Returns:
            The absolute path to the downloaded file.

        Raises:
            NoDownloadLinkError: If no valid download URL is found or conversion is required.
            DownloadError: If the download fails, file exists and overwrite=False, or size mismatch occurs.
            NetworkError: For network-related issues during download.
            RateLimitError: If a login/captcha/non-file page is detected during download.
        """
        # Prepare download target path and final URL using the helper method
        filepath, final_url_to_download = self._prepare_download_target(
            details, download_url, download_dir, filename
        )

        # Check for existing file before making the request
        if not overwrite and os.path.exists(filepath):
            raise DownloadError(f"File exists: {filepath}. Use overwrite=True.")

        dl_response = None
        try:
            # Make the download request using the final URL
            # Pass the final_url_to_download which could be relative or absolute
            dl_response = self._make_request('GET', final_url_to_download, stream=True, allow_redirects=True)
            # Check if the response looks like a file before saving
            self._check_response_content_type(dl_response, final_url_to_download)

            # Save the file content
            with open(filepath, 'wb') as f:
                for chunk in dl_response.iter_content(chunk_size=8192):
                    # Filter out keep-alive new chunks
                    if chunk:
                        f.write(chunk)
            return filepath
        except (NetworkError, DownloadError, RateLimitError, NoDownloadLinkError) as e:
            # Clean up partially downloaded file on error
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass
            raise e  # Re-raise the specific error
        except Exception as e:
            # Clean up on unexpected errors too
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass
            raise DownloadError(f"Unexpected download error for {final_url_to_download} to {filepath}: {e}") from e
        finally:
            # Ensure the response is closed
            if dl_response is not None:
                dl_response.close()

    def download_with_progress(self, details: BookDetails, download_url: Optional[str] = None,
                               download_dir: str = "downloads", filename: Optional[str] = None,
                               overwrite: bool = False) -> Generator[Tuple[int, Optional[int], str], None, str]:
        """
        Downloads a book file yielding progress updates. (Does NOT cache download stream).

        Args:
            details: BookDetails object containing book metadata.
            download_url: Optional specific download URL (relative or absolute).
                          If None, uses details.download_url.
            download_dir: Directory to save the downloaded file.
            filename: Optional filename (without extension). If None, generated from details.
            overwrite: If True, overwrite existing file. Defaults to False.

        Yields:
            Tuples of (current_bytes, total_bytes, status_message).
            Possible status messages: 'connecting', 'downloading', 'progress',
            'warning', 'completed', 'error'.

        Returns:
            The absolute path to the downloaded file upon successful completion.

        Raises:
            NoDownloadLinkError: If no valid download URL is found or conversion is required.
            DownloadError: If the download fails or file exists and overwrite=False.
            NetworkError: For network-related issues during download.
            RateLimitError: If a login/captcha/non-file page is detected during download.
        """
        filepath = None  # Initialize filepath to None
        final_url_to_download = None
        downloaded = 0
        total_size = None
        dl_response = None

        try:
            # Prepare download target path and final URL using the helper method
            filepath, final_url_to_download = self._prepare_download_target(
                details, download_url, download_dir, filename
            )

            # Check for existing file before making the request
            if not overwrite and os.path.exists(filepath):
                yield 0, 0, f"error: File exists: {filepath}. Use overwrite=True."
                raise DownloadError(f"File exists: {filepath}. Use overwrite=True.")

            yield 0, None, f"connecting: {os.path.basename(filepath)}"
            # Make the download request using the final URL
            # Pass the final_url_to_download which could be relative or absolute
            dl_response = self._make_request('GET', final_url_to_download, stream=True, allow_redirects=True)
            # Check if the response looks like a file
            self._check_response_content_type(dl_response, final_url_to_download)

            # Get total size from headers if available
            total_size_str = dl_response.headers.get('content-length')
            if total_size_str and total_size_str.isdigit():
                total_size = int(total_size_str)

            yield 0, total_size, f"downloading: {os.path.basename(filepath)}"

            # Download and write file content in chunks, yielding progress
            with open(filepath, 'wb') as f:
                for chunk in dl_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        yield downloaded, total_size, f"progress: {downloaded}"

            # Final checks and status update
            final_size = downloaded
            if total_size is not None and downloaded != total_size:
                yield downloaded, total_size, f"warning: Size mismatch (header: {total_size}, downloaded: {downloaded})"
            else:
                yield final_size, total_size, f"completed: {filepath}"

            return filepath  # Return filepath on successful completion

        except (NetworkError, DownloadError, RateLimitError, NoDownloadLinkError) as e:
            yield downloaded, total_size, f"error: {e}"
            # Clean up partially downloaded file on error
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass
            raise e  # Re-raise the specific error
        except Exception as e:
            yield downloaded, total_size, f"error: An unexpected error occurred: {e}"
            # Clean up on unexpected errors too
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass
            raise DownloadError(
                f"Unexpected download error for {final_url_to_download or 'unknown URL'} to {filepath or 'unknown path'}: {e}") from e
        finally:
            # Ensure the response is closed
            if dl_response is not None:
                dl_response.close()
