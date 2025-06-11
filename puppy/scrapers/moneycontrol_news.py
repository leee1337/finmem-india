import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
import logging
from puppy.utils.credentials import get_browser_headers
import time

logger = logging.getLogger(__name__)

class MoneyControlNewsScraper:
    """Scraper for MoneyControl news articles"""
    
    BASE_URL = "https://www.moneycontrol.com"

    def __init__(self):
        self.headers = get_browser_headers()
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _make_request(self, url: str, max_retries: int = 3) -> requests.Response:
        """Make HTTP request with retry logic"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise e
                wait_time = (attempt + 1) * 2  # Exponential backoff
                logger.warning(f"Request failed, retrying in {wait_time} seconds...")
                time.sleep(wait_time)

    def get_latest_news(self, page: int = 1, category: str = "all") -> List[Dict]:
        """
        Fetch latest news from MoneyControl
        
        Args:
            page: Page number to fetch (default: 1)
            category: News category (default: 'all')
            
        Returns:
            List of news articles with title, content, date, link and category
        """
        try:
            url = f"{self.BASE_URL}/news/business/page-{page}"
            if category != "all":
                url = f"{self.BASE_URL}/news/{category}/page-{page}"
                
            response = self._make_request(url)
            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.find_all("li", class_="clearfix")
            
            news_list = []
            for article in articles:
                try:
                    title_elem = article.find("h2")
                    if not title_elem:
                        continue
                        
                    title = title_elem.text.strip()
                    link = title_elem.find("a")["href"] if title_elem.find("a") else None
                    
                    content_elem = article.find("p")
                    content = content_elem.text.strip() if content_elem else ""
                    
                    date_elem = article.find("span", class_="date")
                    date_str = date_elem.text.strip() if date_elem else ""
                    
                    news_list.append({
                        "title": title,
                        "content": content,
                        "date": date_str,
                        "link": link,
                        "category": category
                    })
                except Exception as e:
                    logger.error(f"Error parsing article: {str(e)}")
                    continue
                    
            return news_list
            
        except Exception as e:
            logger.error(f"Error fetching news: {str(e)}")
            return []

    def get_stock_news(self, stock_symbol: str, page: int = 1) -> List[Dict]:
        """
        Fetch news specific to a stock/company
        
        Args:
            stock_symbol: Stock symbol on MoneyControl
            page: Page number to fetch (default: 1)
            
        Returns:
            List of company-specific news articles
        """
        try:
            url = f"{self.BASE_URL}/stocks/company-info/{stock_symbol}/news/page-{page}"
            response = self._make_request(url)
            
            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.find_all("div", class_="news-item")
            
            news_list = []
            for article in articles:
                try:
                    title_elem = article.find("h3")
                    if not title_elem:
                        continue
                        
                    title = title_elem.text.strip()
                    link = title_elem.find("a")["href"] if title_elem.find("a") else None
                    
                    content_elem = article.find("p")
                    content = content_elem.text.strip() if content_elem else ""
                    
                    date_elem = article.find("span", class_="date")
                    date_str = date_elem.text.strip() if date_elem else ""
                    
                    news_list.append({
                        "title": title,
                        "content": content,
                        "date": date_str,
                        "link": link,
                        "stock_symbol": stock_symbol
                    })
                except Exception as e:
                    logger.error(f"Error parsing stock news article: {str(e)}")
                    continue
                    
            return news_list
            
        except Exception as e:
            logger.error(f"Error fetching stock news: {str(e)}")
            return []

    def search_news(self, query: str, page: int = 1) -> List[Dict]:
        """
        Search for news articles using a query
        
        Args:
            query: Search query string
            page: Page number to fetch (default: 1)
            
        Returns:
            List of news articles matching the search query
        """
        try:
            url = f"{self.BASE_URL}/news-search/searchresult.php?q={query}&page={page}"
            response = self._make_request(url)
            
            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.find_all("div", class_="search-result-item")
            
            news_list = []
            for article in articles:
                try:
                    title_elem = article.find("h3")
                    if not title_elem:
                        continue
                        
                    title = title_elem.text.strip()
                    link = title_elem.find("a")["href"] if title_elem.find("a") else None
                    
                    content_elem = article.find("p")
                    content = content_elem.text.strip() if content_elem else ""
                    
                    date_elem = article.find("span", class_="date")
                    date_str = date_elem.text.strip() if date_elem else ""
                    
                    news_list.append({
                        "title": title,
                        "content": content,
                        "date": date_str,
                        "link": link,
                        "query": query
                    })
                except Exception as e:
                    logger.error(f"Error parsing search result: {str(e)}")
                    continue
                    
            return news_list
            
        except Exception as e:
            logger.error(f"Error searching news: {str(e)}")
            return [] 