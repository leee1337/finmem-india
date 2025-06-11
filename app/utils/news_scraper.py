import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time
import random
import threading
import queue
from .market_hours import MarketHours

class MoneyControlNewsScraper:
    def __init__(self):
        self.base_url = "https://www.moneycontrol.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive"
        }
    
    def get_latest_news(self, pages: int = 1) -> List[Dict[str, Any]]:
        """Get latest market news from MoneyControl"""
        news_list = []
        
        try:
            for page in range(1, pages + 1):
                url = f"{self.base_url}/news/business/page-{page}"
                response = requests.get(url, headers=self.headers)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find news articles
                articles = soup.find_all('li', class_='clearfix')
                
                for article in articles:
                    try:
                        title_elem = article.find('h2')
                        if not title_elem:
                            continue
                            
                        title = title_elem.text.strip()
                        link = title_elem.find('a')['href'] if title_elem.find('a') else None
                        
                        # Get article timestamp
                        time_elem = article.find('span', class_='date')
                        timestamp = time_elem.text.strip() if time_elem else None
                        
                        # Get article summary
                        summary = article.find('p')
                        summary = summary.text.strip() if summary else None
                        
                        if title and link:
                            news_list.append({
                                'title': title,
                                'link': link,
                                'timestamp': timestamp,
                                'summary': summary
                            })
                    
                    except Exception as e:
                        print(f"Error processing article: {str(e)}")
                        continue
                
                # Add delay between pages
                if page < pages:
                    time.sleep(random.uniform(1, 3))
        
        except Exception as e:
            print(f"Error fetching news: {str(e)}")
        
        return news_list
    
    def get_stock_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Get news for a specific stock from MoneyControl"""
        news_items = []
        try:
            # Try different URL formats
            urls = [
                f"{self.base_url}/stocks/company_info/stock_news.php?sc_id={symbol}",
                f"{self.base_url}/company-article/{symbol}/news/",
                f"{self.base_url}/news/tags/{symbol.lower()}/",
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=self.headers, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Try different article selectors
                    selectors = [
                        '.content_block',  # Main news container
                        '.article_box',    # Alternative container
                        '.MT15',           # Another possible container
                        '.common-article'  # Generic article container
                    ]
                    
                    for selector in selectors:
                        articles = soup.select(selector)
                        if articles:
                            for article in articles:
                                try:
                                    # Extract title
                                    title_elem = (
                                        article.select_one('.content_headline a') or
                                        article.select_one('h2 a') or
                                        article.select_one('.article_title') or
                                        article.select_one('a[class*="title"]')
                                    )
                                    
                                    if not title_elem:
                                        continue
                                    
                                    title = title_elem.get_text(strip=True)
                                    
                                    # Extract summary
                                    summary_elem = (
                                        article.select_one('.content_text') or
                                        article.select_one('.article_desc') or
                                        article.select_one('p')
                                    )
                                    
                                    summary = summary_elem.get_text(strip=True) if summary_elem else "No summary available"
                                    
                                    # Extract link
                                    link = title_elem.get('href', '')
                                    if link and not link.startswith('http'):
                                        link = self.base_url + link
                                    
                                    # Add news item
                                    news_items.append({
                                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                        'source': 'MoneyControl',
                                        'symbol': symbol,
                                        'title': title,
                                        'summary': summary,
                                        'link': link,
                                        'type': self._categorize_news(title + " " + summary)
                                    })
                                
                                except Exception as e:
                                    print(f"Error parsing article for {symbol}: {str(e)}")
                                    continue
                            
                            if news_items:  # If we found news items, break the selector loop
                                break
                    
                    if news_items:  # If we found news items, break the URL loop
                        break
                
                except requests.RequestException as e:
                    print(f"Error fetching URL {url}: {str(e)}")
                    continue
        
        except Exception as e:
            print(f"Error scraping news for {symbol}: {str(e)}")
        
        return news_items
    
    def search_news(self, query: str, pages: int = 1) -> List[Dict[str, Any]]:
        """Search news articles by keyword"""
        news_list = []
        
        try:
            for page in range(1, pages + 1):
                url = f"{self.base_url}/news/searchresult.php?q={query}&page={page}"
                response = requests.get(url, headers=self.headers)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find news articles
                articles = soup.find_all('div', class_='search_result')
                
                for article in articles:
                    try:
                        title_elem = article.find('h3')
                        if not title_elem:
                            continue
                            
                        title = title_elem.text.strip()
                        link = title_elem.find('a')['href'] if title_elem.find('a') else None
                        
                        # Get article timestamp
                        time_elem = article.find('span', class_='date')
                        timestamp = time_elem.text.strip() if time_elem else None
                        
                        # Get article summary
                        summary = article.find('p')
                        summary = summary.text.strip() if summary else None
                        
                        if title and link:
                            news_list.append({
                                'title': title,
                                'link': link,
                                'timestamp': timestamp,
                                'summary': summary
                            })
                    
                    except Exception as e:
                        print(f"Error processing article: {str(e)}")
                        continue
                
                # Add delay between pages
                if page < pages:
                    time.sleep(random.uniform(1, 3))
        
        except Exception as e:
            print(f"Error searching news: {str(e)}")
        
        return news_list
    
    def _categorize_news(self, text: str) -> str:
        """Categorize news based on content"""
        text = text.lower()
        
        categories = {
            'Earnings': ['earnings', 'revenue', 'profit', 'loss', 'quarterly', 'financial results'],
            'Corporate Action': ['dividend', 'bonus', 'split', 'merger', 'acquisition'],
            'Management': ['appoints', 'resigns', 'board', 'director', 'ceo', 'management'],
            'Regulatory': ['sebi', 'rbi', 'regulation', 'compliance', 'penalty'],
            'Market Update': ['stock', 'share', 'market', 'trading', 'price'],
            'Business Update': ['launches', 'expansion', 'contract', 'partnership', 'deal']
        }
        
        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return 'General'

class NewsScraperThread(threading.Thread):
    def __init__(self, symbol: str, news_queue: queue.Queue):
        super().__init__()
        self.symbol = symbol
        self.news_queue = news_queue
        self.running = True
        self.daemon = True  # Thread will exit when main program exits
    
    def run(self):
        """Run news scraping for the assigned symbol"""
        while self.running:
            try:
                # Scrape from multiple sources
                news_items = []
                news_items.extend(self._scrape_moneycontrol())
                news_items.extend(self._scrape_economic_times())
                news_items.extend(self._scrape_business_standard())
                
                # Add news items to queue
                for item in news_items:
                    self.news_queue.put({
                        'symbol': self.symbol,
                        'news': item
                    })
                
                # Sleep between scrapes
                time.sleep(60)  # 1 minute delay between scrapes
                
            except Exception as e:
                print(f"Error scraping news for {self.symbol}: {str(e)}")
                time.sleep(60)  # Wait before retrying
    
    def _scrape_moneycontrol(self) -> List[Dict[str, Any]]:
        """Scrape news from MoneyControl"""
        news_items = []
        try:
            # MoneyControl search URL
            url = f"https://www.moneycontrol.com/stocks/company_info/stock_news.php?sc_id={self.symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract news items
            for article in soup.select('.content_block'):
                try:
                    news_items.append({
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'MoneyControl',
                        'title': article.select_one('.content_headline a').text.strip(),
                        'summary': article.select_one('.content_text').text.strip(),
                        'link': article.select_one('.content_headline a')['href'],
                        'type': self._categorize_news(article.text)
                    })
                except Exception as e:
                    print(f"Error parsing MoneyControl article: {str(e)}")
        
        except Exception as e:
            print(f"Error scraping MoneyControl: {str(e)}")
        
        return news_items
    
    def _scrape_economic_times(self) -> List[Dict[str, Any]]:
        """Scrape news from Economic Times"""
        news_items = []
        try:
            # Economic Times search URL with the stock symbol
            url = f"https://economictimes.indiatimes.com/markets/stocks/news"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try different possible article selectors
            articles = []
            selectors = [
                '.eachStory',  # Main article container
                '.story_list',  # Alternative container
                '.newslist',    # Another possible container
                'div[data-tracking-name="Story_List"]'  # Data attribute based selector
            ]
            
            for selector in selectors:
                articles = soup.select(selector)
                if articles:
                    break
            
            # Extract news items related to the symbol
            for article in articles:
                try:
                    # Try different title selectors
                    title_elem = (
                        article.select_one('.title') or 
                        article.select_one('h3') or 
                        article.select_one('.story_title') or
                        article.select_one('a[data-tracking-name="Story_Title"]')
                    )
                    
                    if not title_elem:
                        continue
                        
                    title = title_elem.get_text(strip=True)
                    
                    # Only process if title contains the symbol
                    if self.symbol.lower() in title.lower():
                        # Try different summary selectors
                        summary_elem = (
                            article.select_one('.summary') or 
                            article.select_one('.desc') or 
                            article.select_one('.story_desc') or
                            article.select_one('p')
                        )
                        
                        summary = summary_elem.get_text(strip=True) if summary_elem else "No summary available"
                        
                        # Try different link selectors
                        link_elem = (
                            title_elem.get('href') or 
                            article.select_one('a').get('href') if article.select_one('a') else None
                        )
                        
                        if link_elem:
                            # Make sure link is absolute
                            if not link_elem.startswith('http'):
                                link_elem = 'https://economictimes.indiatimes.com' + link_elem
                        else:
                            link_elem = url  # Use main URL if no specific link found
                        
                        news_items.append({
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'source': 'Economic Times',
                            'title': title,
                            'summary': summary,
                            'link': link_elem,
                            'type': self._categorize_news(title + " " + summary)
                        })
                
                except Exception as e:
                    print(f"Error parsing individual Economic Times article: {str(e)}")
                    continue
        
        except requests.RequestException as e:
            print(f"Network error scraping Economic Times: {str(e)}")
        except Exception as e:
            print(f"Error scraping Economic Times: {str(e)}")
        
        return news_items
    
    def _scrape_business_standard(self) -> List[Dict[str, Any]]:
        """Scrape news from Business Standard"""
        news_items = []
        try:
            # Business Standard search URL
            url = f"https://www.business-standard.com/search?type=news&q={self.symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try different article selectors
            articles = []
            selectors = [
                '.article',
                '.story-card',
                '.news-item',
                '.searchNews'
            ]
            
            for selector in selectors:
                articles = soup.select(selector)
                if articles:
                    break
            
            for article in articles:
                try:
                    # Try different title selectors
                    title_elem = (
                        article.select_one('.headline') or
                        article.select_one('h2') or
                        article.select_one('.article-title') or
                        article.select_one('a[class*="title"]')
                    )
                    
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # Try different summary selectors
                    summary_elem = (
                        article.select_one('.summary') or
                        article.select_one('.description') or
                        article.select_one('.article-desc') or
                        article.select_one('p')
                    )
                    
                    summary = summary_elem.get_text(strip=True) if summary_elem else "No summary available"
                    
                    # Try different link selectors
                    link_elem = article.select_one('a')
                    link = link_elem.get('href') if link_elem else None
                    
                    if link:
                        # Make sure link is absolute
                        if not link.startswith('http'):
                            link = 'https://www.business-standard.com' + link
                    else:
                        link = url  # Use main URL if no specific link found
                    
                    news_items.append({
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'Business Standard',
                        'title': title,
                        'summary': summary,
                        'link': link,
                        'type': self._categorize_news(title + " " + summary)
                    })
                
                except Exception as e:
                    print(f"Error parsing Business Standard article: {str(e)}")
                    continue
        
        except requests.RequestException as e:
            print(f"Network error scraping Business Standard: {str(e)}")
        except Exception as e:
            print(f"Error scraping Business Standard: {str(e)}")
        
        return news_items
    
    def _categorize_news(self, text: str) -> str:
        """Categorize news based on content"""
        text = text.lower()
        
        categories = {
            'Earnings': ['earnings', 'revenue', 'profit', 'loss', 'quarterly', 'financial results'],
            'Corporate Action': ['dividend', 'bonus', 'split', 'merger', 'acquisition'],
            'Management': ['appoints', 'resigns', 'board', 'director', 'ceo', 'management'],
            'Regulatory': ['sebi', 'rbi', 'regulation', 'compliance', 'penalty'],
            'Market Update': ['stock', 'share', 'market', 'trading', 'price'],
            'Business Update': ['launches', 'expansion', 'contract', 'partnership', 'deal']
        }
        
        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return 'General'
    
    def stop(self):
        """Stop the news scraping thread"""
        self.running = False

class NewsAggregator:
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.news_queue = queue.Queue()
        self.scrapers = {}
        self.market_hours = MarketHours()
        self.running = False
        self.latest_news = []
        self.max_news = 100  # Maximum number of news items to keep
        self.moneycontrol = MoneyControlNewsScraper()  # Initialize MoneyControl scraper
        self.last_news_fetch = {}  # Track last fetch time for each symbol
        self.news_fetch_interval = timedelta(minutes=5)  # Fetch news every 5 minutes
    
    def start(self):
        """Start news aggregation for all symbols"""
        if self.running:
            return
        
        self.running = True
        
        # Start scraper threads for each symbol
        for symbol in self.symbols:
            scraper = NewsScraperThread(symbol, self.news_queue)
            self.scrapers[symbol] = scraper
            scraper.start()
            self.last_news_fetch[symbol] = datetime.min  # Initialize last fetch time
        
        # Start news processing thread
        self.processor_thread = threading.Thread(target=self._process_news)
        self.processor_thread.daemon = True
        self.processor_thread.start()
        
        # Initial news fetch for all symbols
        self._fetch_all_news()
    
    def _fetch_all_news(self):
        """Fetch news for all symbols from MoneyControl"""
        for symbol in self.symbols:
            try:
                news_items = self.moneycontrol.get_stock_news(symbol)
                for item in news_items:
                    self.news_queue.put({
                        'symbol': symbol,
                        'news': item
                    })
                self.last_news_fetch[symbol] = datetime.now()
            except Exception as e:
                print(f"Error fetching news for {symbol}: {str(e)}")
    
    def _process_news(self):
        """Process news items from queue"""
        while self.running:
            try:
                # Check if we need to fetch fresh news
                current_time = datetime.now()
                for symbol in self.symbols:
                    if current_time - self.last_news_fetch[symbol] > self.news_fetch_interval:
                        news_items = self.moneycontrol.get_stock_news(symbol)
                        for item in news_items:
                            self.news_queue.put({
                                'symbol': symbol,
                                'news': item
                            })
                        self.last_news_fetch[symbol] = current_time
                
                # Process news from queue
                try:
                    news_data = self.news_queue.get(timeout=1)
                    
                    # Add to latest news
                    self.latest_news.insert(0, {
                        'timestamp': news_data['news']['timestamp'],
                        'symbol': news_data['symbol'],
                        'source': news_data['news']['source'],
                        'type': news_data['news']['type'],
                        'title': news_data['news']['title'],
                        'summary': news_data['news']['summary'],
                        'link': news_data['news']['link']
                    })
                    
                    # Keep only recent news
                    if len(self.latest_news) > self.max_news:
                        self.latest_news = self.latest_news[:self.max_news]
                    
                except queue.Empty:
                    continue
                
            except Exception as e:
                print(f"Error processing news: {str(e)}")
                time.sleep(1)
    
    def get_latest_news(self, limit: int = None, symbol: str = None, news_type: str = None) -> List[Dict[str, Any]]:
        """Get latest news with optional filtering"""
        news = self.latest_news
        
        # Apply filters
        if symbol:
            news = [item for item in news if item['symbol'] == symbol]
        if news_type:
            news = [item for item in news if item['type'] == news_type]
        
        # Apply limit
        if limit:
            news = news[:limit]
        
        return news
    
    def get_news_summary(self) -> Dict[str, Any]:
        """Get summary of news activity"""
        return {
            'total_news': len(self.latest_news),
            'sources': len(set(item['source'] for item in self.latest_news)),
            'symbols_covered': len(set(item['symbol'] for item in self.latest_news)),
            'latest_update': self.latest_news[0]['timestamp'] if self.latest_news else None
        } 