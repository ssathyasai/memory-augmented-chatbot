"""Web scraping module for fetching current data."""

import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class WebScraper:
    """Web scraper for fetching current data from the web."""
    
    def __init__(self):
        """Initialize the web scraper."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Search the web for information about a query.
        
        Args:
            query: Search query
            max_results: Maximum number of results
        
        Returns:
            List of search results with titles, URLs, and content
        """
        results = []
        
        # Try Google search (public search endpoint)
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        
        try:
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract search results
                for result in soup.select('div.g')[:max_results]:
                    title_elem = result.select_one('h3')
                    link_elem = result.select_one('a')
                    
                    if title_elem and link_elem:
                        title = title_elem.get_text()
                        link = link_elem.get('href', '')
                        
                        # Clean the URL
                        if link.startswith('/url?q='):
                            link = link.split('?q=')[1].split('&')[0]
                        
                        # Fetch the page content
                        content = self._fetch_page_content(link) if link else ""
                        
                        results.append({
                            'title': title,
                            'url': link,
                            'content': content
                        })
        
        except Exception as e:
            logger.error(f"Search error for '{query}': {e}")
        
        return results
    
    def _fetch_page_content(self, url: str, max_length: int = 2000) -> str:
        """
        Fetch page content from a URL.
        
        Args:
            url: URL to fetch
            max_length: Maximum content length
        
        Returns:
            Page content as text
        """
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove scripts and styles
                for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                    script.decompose()
                
                # Get text content
                text = soup.get_text(separator=' ', strip=True)
                
                # Clean up whitespace
                lines = [line.strip() for line in text.splitlines()]
                text = ' '.join([line for line in lines if line])
                
                # Truncate if too long
                if len(text) > max_length:
                    text = text[:max_length] + "..."
                
                return text
        
        except Exception as e:
            logger.warning(f"Failed to fetch page content from {url}: {e}")
        
        return ""
    
    def scrape_specific_page(self, url: str) -> Optional[Dict[str, str]]:
        """
        Scrape a specific web page.
        
        Args:
            url: URL to scrape
        
        Returns:
            Dictionary with title and content, or None if failed
        """
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Get title
                title = soup.title.string if soup.title else "No title"
                
                # Get main content
                content = self._fetch_page_content(url, max_length=3000)
                
                return {
                    'title': title,
                    'url': url,
                    'content': content
                }
        
        except Exception as e:
            logger.error(f"Failed to scrape page {url}: {e}")
        
        return None
    
    def get_current_date(self) -> str:
        """Get the current date from a reliable source."""
        try:
            response = self.session.get("https://www.timeanddate.com/", timeout=5)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try to extract date from various locations
                date_elem = soup.find(['time', 'span', 'div'], 
                                    attrs={'class': lambda x: x and any(
                                        c in str(x).lower() for c in ['date', 'time', 'today']
                                    )})
                
                if date_elem:
                    return date_elem.get_text(strip=True)
        
        except Exception:
            pass
        
        # Fallback to current system date
        from datetime import datetime
        return datetime.now().strftime("%B %d, %Y")


# Global instance
web_scraper = WebScraper()
