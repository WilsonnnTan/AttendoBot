import re
import json
import requests
import logging

    
# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Set the logging level
    format='%(asctime)s - %(levelname)s - %(message)s',  # Define the log message format
    handlers=[
        logging.StreamHandler()  # Output logs to the console
    ]
)
logger = logging.getLogger(__name__)  # Create a logger for this module


def extract_google_form_url(url):
    """
    Extracts both 'viewform' and 'formResponse' URLs from a Google Form link.

    Supports shortened URLs (forms.gle) by following redirects. Returns:
    - view_url: for reading form fields
    - post_url: for submitting data via POST

    Args:
        url (str): Shortened or full Google Form URL.

    Returns:
        tuple[str | None, str | None]: (view_url, post_url), or (None, None) on failure.
    """
    try:
        # If it's a shortened URL (forms.gle), expand it
        if "forms.gle" in url:
            response = requests.get(url, allow_redirects=True)
            url = response.url  # Expand to full URL

        # Try to extract form ID
        match = re.search(r'/d/e/([a-zA-Z0-9_-]+)/viewform', url)
        if match:
            form_id = match.group(1)
            view_url = f"https://docs.google.com/forms/d/e/{form_id}/viewform"
            post_url = f"https://docs.google.com/forms/d/e/{form_id}/formResponse"
            return view_url, post_url 
        else:
            logger.warning("Couldn't find the Google Form ID in the URL.")
            return None, None
    except Exception as e:
        logger.error(f"Error while extracting form ID: {e}")
        return None, None


def POST_Request_to_GForm(url, data):
    """
    Sends a POST request with `data` (a dict of entry IDs → values)
    to the Google Form URL specified in the environment.

    Returns:
        True if submission succeeds (HTTP 2xx), False otherwise.
    """
    try:
        response = requests.post(url, data=data, timeout=10)
        return True

    except requests.RequestException as e:
        # Catches connection errors, timeouts, HTTP errors, etc.
        logger.error(e)
        return False
    

def get_GForm_data(url):
    """
    Fetches the hidden JSON payload from a Google Form page.
    """
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()  # raises HTTPError on 4xx/5xx :contentReference[oaicite:3]{index=3}

        match = re.search(r'FB_PUBLIC_LOAD_DATA_ = (.*?);', response.text, flags=re.S)
        data = json.loads(match.group(1))
        return data

    except Exception as e:
        logger.error(f"Error saat mengambil data Google Form: {e}")
        return None


def get_ids(d):
    """
    Recursively traverses a nested dict/list structure to find all
    Google Form entry IDs. Google Forms embeds each field's entry ID
    in a list of length 3 where the middle element is None, like:
      [123456789, None, ...]
    This function yields each such ID it encounters.

    Args:
        d (dict or list): The parsed FB_PUBLIC_LOAD_DATA_ structure.

    Yields:
        int: An entry ID corresponding to a form field.
    """
    if isinstance(d, dict):
        for k, v in d.items():
            yield from get_ids(v)
    elif isinstance(d, list):
        if len(d) == 3 and d[1] is None:
            yield d[0]
        else:
            for v in d:
                yield from get_ids(v)
