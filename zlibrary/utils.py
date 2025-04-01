# zlibrary_api/utils.py
# -*- coding: utf-8 -*-

import re
import requests
from urllib.parse import urljoin

# --- Constants ---
DEFAULT_BASE_URL = "https://z-library.sk" # Example default, user can override
SEARCH_PATH = "/s/"
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36' # Reasonably modern UA


# --- Helper Functions ---
def sanitize_filename(filename: str) -> str:
    """Removes illegal characters and truncates filename for compatibility."""
    if not isinstance(filename, str):
        filename = str(filename)

    # Remove characters illegal in Windows/Linux/MacOS filenames
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Replace control characters (0x00-0x1F) except tab, newline, return
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', sanitized)
    # Replace multiple dots with a single dot
    sanitized = re.sub(r'\.{2,}', '.', sanitized)
    # Replace multiple spaces with a single space
    sanitized = re.sub(r'\s{2,}', ' ', sanitized)
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    # Truncate filename to avoid OS limits (e.g., 255 bytes/chars)
    max_len = 200 # A conservative limit
    # Encode to check byte length, decode ignoring errors for truncation
    if len(sanitized.encode('utf-8', 'ignore')) > max_len:
        # Try to truncate at the last space within the limit
        truncated_bytes = sanitized.encode('utf-8', 'ignore')[:max_len]
        truncated_string = truncated_bytes.decode('utf-8', 'ignore')
        # Find last space in the potentially multi-byte truncated string
        last_space = truncated_string.rfind(' ')
        if last_space > 0:
            sanitized = truncated_string[:last_space]
        else:
            # Force truncate if no space found or if it results in empty string
            sanitized = truncated_string

    # Ensure the filename is not empty after sanitization
    if not sanitized:
        sanitized = "downloaded_file" # Default fallback name
    return sanitized


def create_session(base_url: str = DEFAULT_BASE_URL, user_agent: str = DEFAULT_USER_AGENT) -> requests.Session:
    """Creates and configures a requests Session."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': user_agent,
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7', # Modern Accept header
        'Connection': 'keep-alive',
        'DNT': '1',  # Do Not Track
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document', # Common browser headers
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin', # Adjust if needed, but good default
        'Referer': base_url # Initial referer
    })
    return session