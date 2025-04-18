import re
import json
import requests
import logging

class GoogleFormHandler:
    """Handles Google Form interactions including URL extraction, data fetching, and submissions."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def extract_urls(self, url: str) -> tuple[str | None, str | None]:
        """
        Extracts both 'viewform' and 'formResponse' URLs from a Google Form link.
        
        Args:
            url (str): Shortened or full Google Form URL
            
        Returns:
            tuple: (view_url, post_url) or (None, None) on failure
        """
        try:
            # Expand shortened URLs
            if "forms.gle" in url:
                response = requests.get(url, allow_redirects=True)
                url = response.url

            # Extract form ID
            match = re.search(r'/d/e/([a-zA-Z0-9_-]+)/viewform', url)
            if match:
                form_id = match.group(1)
                return (
                    f"https://docs.google.com/forms/d/e/{form_id}/viewform",
                    f"https://docs.google.com/forms/d/e/{form_id}/formResponse"
                )
            self.logger.warning("Couldn't find Google Form ID in URL")
            return None, None
            
        except Exception as e:
            self.logger.error(f"URL extraction failed: {e}")
            return None, None

    def submit_response(self, post_url: str, data: dict) -> bool:
        """
        Submits data to Google Form.
        
        Args:
            post_url (str): Form's submission endpoint
            data (dict): Form data {field_id: value}
            
        Returns:
            bool: True if successful
        """
        try:
            response = requests.post(post_url, data=data, timeout=10)
            return response.ok
        except requests.RequestException as e:
            self.logger.error(f"Submission failed: {e}")
            return False

    def fetch_form_data(self, view_url: str) -> list | dict | None:
        """
        Fetches hidden configuration data from Google Form.
        
        Args:
            view_url (str): Form's viewform URL
            
        Returns:
            Parsed JSON data or None
        """
        try:
            response = requests.get(view_url, timeout=15)
            response.raise_for_status()
            match = re.search(r'FB_PUBLIC_LOAD_DATA_ = (.*?);', response.text, flags=re.S)
            return json.loads(match.group(1))
        except Exception as e:
            self.logger.error(f"Data fetch failed: {e}")
            return None

    @staticmethod
    def get_entry_ids(data: dict | list) -> iter:
        """
        Recursively finds all field IDs in form data.
        
        Args:
            data: Parsed FB_PUBLIC_LOAD_DATA_ structure
            
        Yields:
            int: Field entry IDs
        """
        if isinstance(data, dict):
            for v in data.values():
                yield from GoogleFormHandler.get_entry_ids(v)
        elif isinstance(data, list):
            if len(data) == 3 and data[1] is None:
                yield data[0]
            else:
                for item in data:
                    yield from GoogleFormHandler.get_entry_ids(item)

# Configure logging at module level
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)