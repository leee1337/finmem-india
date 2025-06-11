from typing import List, Dict
from puppy.scrapers.moneycontrol_news import MoneyControlNewsScraper
from loguru import logger

class NewsService:
    """Service for fetching and managing news data"""
    
    def __init__(self):
        self.news_scraper = MoneyControlNewsScraper()
        
    def get_latest_market_news(self, pages: int = 1) -> List[Dict]:
        """
        Get latest market news from MoneyControl
        
        Args:
            pages: Number of pages to fetch (default: 1)
            
        Returns:
            List of news articles
        """
        all_news = []
        for page in range(1, pages + 1):
            news = self.news_scraper.get_latest_news(page=page)
            if news:
                all_news.extend(news)
            else:
                break
                
        logger.info(f"Fetched {len(all_news)} market news articles")
        return all_news
        
    def get_stock_specific_news(self, symbols: List[str], pages_per_stock: int = 1) -> Dict[str, List[Dict]]:
        """
        Get news specific to given stock symbols
        
        Args:
            symbols: List of stock symbols
            pages_per_stock: Number of pages to fetch per stock (default: 1)
            
        Returns:
            Dictionary mapping stock symbols to their news articles
        """
        stock_news = {}
        for symbol in symbols:
            news_list = []
            for page in range(1, pages_per_stock + 1):
                news = self.news_scraper.get_stock_news(symbol, page=page)
                if news:
                    news_list.extend(news)
                else:
                    break
            stock_news[symbol] = news_list
            logger.info(f"Fetched {len(news_list)} news articles for {symbol}")
            
        return stock_news
        
    def search_market_news(self, query: str, pages: int = 1) -> List[Dict]:
        """
        Search for news articles using a query
        
        Args:
            query: Search query string
            pages: Number of pages to fetch (default: 1)
            
        Returns:
            List of news articles matching the query
        """
        all_news = []
        for page in range(1, pages + 1):
            news = self.news_scraper.search_news(query, page=page)
            if news:
                all_news.extend(news)
            else:
                break
                
        logger.info(f"Found {len(all_news)} news articles for query: {query}")
        return all_news 