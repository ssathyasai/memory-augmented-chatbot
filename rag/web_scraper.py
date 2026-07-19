"""Web search and html scraping tool module.

Process Flow:
1. Formats search query and requests DuckDuckGo HTML endpoint using custom User-Agent headers.
2. Uses `BeautifulSoup` to parse HTML result cards, extracting titles, redirect URLs, and snippets.
3. Unpacks actual destination URLs from search redirects using `urllib.parse`.
4. Attempts deep fetching of full web page content (`_fetch_page_content`) with paragraph text extraction.
5. Returns structured web context dictionary array `[{title, url, content}]`.
"""

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
            'User-Agent': 'Mozilla/5.0'
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
        
        # Query DuckDuckGo HTML search endpoint (which is extremely friendly to scrapers)
        import urllib.parse
        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        try:
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract search results
                items = soup.select('div.result')
                for item in items[:max_results]:
                    title_elem = item.select_one('a.result__a')
                    snippet_elem = item.select_one('a.result__snippet')
                    
                    if title_elem:
                        title = title_elem.get_text().strip()
                        raw_link = title_elem.get('href', '')
                        
                        # Extract the actual destination URL from the DuckDuckGo redirect link
                        from urllib.parse import urlparse, parse_qs
                        parsed = urlparse(raw_link)
                        qs = parse_qs(parsed.query)
                        link = qs.get('uddg', [raw_link])[0]
                        
                        if link.startswith('//'):
                            link = 'https:' + link
                        elif link.startswith('/'):
                            link = 'https://duckduckgo.com' + link
                            
                        # Use description snippet as base content, and try to fetch page content if possible
                        snippet = snippet_elem.get_text().strip() if snippet_elem else ""
                        
                        # Try to fetch full page content (fallback to snippet if it fails or times out)
                        content = ""
                        try:
                            content = self._fetch_page_content(link) if link else ""
                        except Exception as e:
                            logger.warning(f"Failed to fetch content for {link}: {e}")
                            
                        if not content:
                            content = snippet
                            
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
            response = self.session.get(url, timeout=3)
            
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
