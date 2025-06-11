import yfinance as yf
import pandas as pd
from typing import Dict, Any, List
from loguru import logger
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
from nsepy import get_history
from nsepy.derivatives import get_expiry_date
import time
import os
from .credentials import CredentialsManager

class FinancialDataLoader:
    def __init__(self, config: Dict[str, Any]):
        self.symbols = config["symbols"]
        self.screener_url = "https://www.screener.in/company/{}/consolidated/"
        self.moneycontrol_url = "https://www.moneycontrol.com/india/stockpricequote/"
        
        # Initialize credentials manager
        self.credentials = CredentialsManager()
        
        # Try to load existing sessions
        self.credentials.load_session_cookies()
        
        # Initialize sessions
        self.screener_session = self.credentials.get_screener_session()
        self.moneycontrol_session = self.credentials.get_moneycontrol_session()
        self.nse_headers = self.credentials.get_nse_headers()
        
    def __del__(self):
        """Save sessions on cleanup"""
        if hasattr(self, 'credentials'):
            self.credentials.save_session_cookies()
        
    def fetch_quarterly_reports(self, symbol: str) -> Dict[str, Any]:
        """Fetch quarterly financial reports from multiple sources"""
        try:
            # Clean symbol for different APIs
            clean_symbol = symbol.replace('.NS', '')
            
            # Initialize data dictionary
            quarterly_data = {
                "income_stmt": {},
                "balance_sheet": {},
                "cash_flow": {},
                "key_ratios": {},
                "shareholding": {}
            }
            
            # 1. Fetch NSE data
            try:
                nse_data = self._fetch_nse_data(clean_symbol)
                quarterly_data.update(nse_data)
            except Exception as e:
                logger.warning(f"Error fetching NSE data for {symbol}: {e}")
            
            # 2. Fetch from Screener.in
            try:
                screener_data = self._fetch_screener_data(clean_symbol)
                quarterly_data.update(screener_data)
            except Exception as e:
                logger.warning(f"Error fetching Screener.in data for {symbol}: {e}")
            
            # 3. Use yfinance for comprehensive data
            try:
                stock = yf.Ticker(symbol)
                
                # Get quarterly financials
                if hasattr(stock, 'quarterly_financials'):
                    quarterly_data["income_stmt"].update(stock.quarterly_financials.to_dict())
                
                # Get quarterly balance sheet
                if hasattr(stock, 'quarterly_balance_sheet'):
                    quarterly_data["balance_sheet"].update(stock.quarterly_balance_sheet.to_dict())
                
                # Get quarterly cash flow
                if hasattr(stock, 'quarterly_cashflow'):
                    quarterly_data["cash_flow"].update(stock.quarterly_cashflow.to_dict())
                
                # Get institutional holders
                if hasattr(stock, 'institutional_holders'):
                    holdings = stock.institutional_holders
                    if holdings is not None:
                        quarterly_data["shareholding"]["institutional"] = holdings.to_dict()
                
                # Get major holders
                if hasattr(stock, 'major_holders'):
                    holdings = stock.major_holders
                    if holdings is not None:
                        quarterly_data["shareholding"]["major"] = holdings.to_dict()
                    
            except Exception as e:
                logger.warning(f"Error fetching Yahoo Finance data for {symbol}: {e}")
            
            return quarterly_data
            
        except Exception as e:
            logger.error(f"Error fetching quarterly data for {symbol}: {e}")
            return {}
    
    def _fetch_nse_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch data from NSE"""
        try:
            # Get stock history from NSE
            end = datetime.now()
            start = end - timedelta(days=365)  # Last 1 year
            
            # Add NSE API headers if available
            kwargs = {}
            if self.nse_headers:
                kwargs['headers'] = self.nse_headers
            
            stock_data = get_history(
                symbol=symbol,
                start=start,
                end=end,
                **kwargs
            )
            
            # Set datetime index
            stock_data.index = pd.to_datetime(stock_data.index)
            
            # Calculate quarterly aggregates
            quarterly = stock_data.resample('QE').agg({
                'High': 'max',
                'Low': 'min',
                'Volume': 'sum',
                'Turnover': 'sum',
                'Trades': 'sum',
                'Deliverable Volume': 'sum'
            })
            
            return {
                "nse_quarterly": quarterly.to_dict(),
                "delivery_percentage": (stock_data['Deliverable Volume'] / stock_data['Volume']).mean(),
                "avg_trading_volume": stock_data['Volume'].mean()
            }
            
        except Exception as e:
            logger.error(f"Error fetching NSE data: {e}")
            return {}
    
    def _fetch_screener_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch data from Screener.in"""
        try:
            if not self.screener_session:
                # Try to get a new session
                self.screener_session = self.credentials.get_screener_session()
                if not self.screener_session:
                    return {}
            
            url = self.screener_url.format(symbol)
            
            # Add delay to respect rate limits
            time.sleep(1)
            
            response = self.screener_session.get(url)
            if response.status_code == 401:
                # Session expired, try to get a new one
                self.screener_session = self.credentials.get_screener_session()
                if self.screener_session:
                    response = self.screener_session.get(url)
            
            if response.status_code != 200:
                return {}
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract quarterly results table
            quarterly_tables = soup.find_all('table', {'class': 'data-table'})
            
            data = {}
            for table in quarterly_tables:
                # Find table title
                title = table.find_previous('h2').text.strip()
                
                # Extract headers and data
                headers = [th.text.strip() for th in table.find_all('th')]
                rows = []
                for tr in table.find_all('tr')[1:]:  # Skip header row
                    row = [td.text.strip() for td in tr.find_all('td')]
                    if row:
                        rows.append(row)
                
                if rows:
                    df = pd.DataFrame(rows, columns=headers)
                    data[title] = df.to_dict()
            
            return {"screener_data": data}
            
        except Exception as e:
            logger.error(f"Error fetching Screener.in data: {e}")
            return {}
    
    def _fetch_moneycontrol_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch data from MoneyControl without authentication"""
        try:
            session = requests.Session()
            
            # Set browser-like headers
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            # Function for exponential backoff
            def exponential_backoff(attempt):
                wait_time = min(300, (2 ** attempt)) # Cap at 5 minutes
                logger.info(f"Rate limit hit, waiting {wait_time} seconds before retry (attempt {attempt + 1})")
                time.sleep(wait_time)
            
            # First get the company's MoneyControl page URL
            max_retries = 5
            search_url = f"https://www.moneycontrol.com/stocks/cptmarket/compsearchnew.php?search_data={symbol}&cid=&mbsearch_str=&topsearch_type=1&search_str={symbol}"
            
            # Try to get the search page with retries
            for attempt in range(max_retries):
                try:
                    response = session.get(search_url, timeout=30)
                    if response.status_code == 200:
                        break
                    elif response.status_code == 429:  # Rate limit hit
                        exponential_backoff(attempt)
                        continue
                    elif response.status_code == 503:  # Service unavailable
                        logger.warning(f"MoneyControl service temporarily unavailable (attempt {attempt + 1})")
                        exponential_backoff(attempt)
                        continue
                    else:
                        raise Exception(f"Failed to get search page: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise Exception(f"Max retries reached: {str(e)}")
                    exponential_backoff(attempt)
                    continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the first stock link which should be the most relevant match
            stock_link = soup.find('a', {'class': 'bl_12'})
            if not stock_link:
                return {}
            
            stock_url = stock_link.get('href')
            if not stock_url:
                return {}
            
            # Add delay to respect rate limits
            time.sleep(1)
            
            # Get the stock page with retries
            for attempt in range(max_retries):
                try:
                    response = session.get(stock_url, timeout=30)
                    if response.status_code == 200:
                        break
                    elif response.status_code == 429:  # Rate limit hit
                        exponential_backoff(attempt)
                        continue
                    elif response.status_code == 503:  # Service unavailable
                        logger.warning(f"MoneyControl service temporarily unavailable (attempt {attempt + 1})")
                        exponential_backoff(attempt)
                        continue
                    else:
                        raise Exception(f"Failed to get stock page: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise Exception(f"Max retries reached: {str(e)}")
                    exponential_backoff(attempt)
                    continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract key financial ratios
            ratios = {}
            ratio_blocks = soup.find_all('div', {'class': ['ratio_block', 'financial_ratio']})
            for block in ratio_blocks:
                label = block.find('div', {'class': ['ratio_label', 'label']})
                value = block.find('div', {'class': ['ratio_value', 'value']})
                if label and value:
                    ratios[label.text.strip()] = value.text.strip()
            
            # Extract shareholding pattern
            shareholding = {}
            holding_table = soup.find('table', {'class': ['share_hold', 'shareholding']})
            if holding_table:
                rows = holding_table.find_all('tr')
                for row in rows[1:]:  # Skip header
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        category = cols[0].text.strip()
                        percentage = cols[1].text.strip()
                        shareholding[category] = percentage
            
            # Extract quarterly results
            quarterly = {}
            results_table = soup.find('table', {'class': ['mctable1', 'quarterly_results']})
            if results_table:
                headers = [th.text.strip() for th in results_table.find_all('th')]
                rows = []
                for tr in results_table.find_all('tr')[1:]:  # Skip header row
                    row = [td.text.strip() for td in tr.find_all('td')]
                    if row:
                        rows.append(row)
                if rows:
                    quarterly['results'] = pd.DataFrame(rows, columns=headers).to_dict()
            
            return {
                "moneycontrol_ratios": ratios,
                "shareholding_pattern": shareholding,
                "quarterly_results": quarterly
            }
            
        except Exception as e:
            logger.error(f"Error fetching MoneyControl data: {e}")
            return {}
    
    def fetch_fundamental_metrics(self, symbol: str) -> Dict[str, Any]:
        """Fetch fundamental metrics and ratios"""
        try:
            metrics = {}
            
            # 1. Get NSE data
            try:
                nse_data = self._fetch_nse_data(symbol.replace('.NS', ''))
                metrics.update(nse_data)
            except Exception:
                pass
            
            # 2. Get Screener.in data
            try:
                screener_data = self._fetch_screener_data(symbol.replace('.NS', ''))
                if 'screener_data' in screener_data:
                    ratios = screener_data['screener_data'].get('Key Ratios', {})
                    metrics.update(ratios)
            except Exception:
                pass
            
            # 3. Get comprehensive data from Yahoo Finance
            try:
                stock = yf.Ticker(symbol)
                info = stock.info
                
                # Basic metrics
                metrics.update({
                    "pe_ratio": info.get('trailingPE'),
                    "forward_pe": info.get('forwardPE'),
                    "pb_ratio": info.get('priceToBook'),
                    "market_cap": info.get('marketCap'),
                    "enterprise_value": info.get('enterpriseValue'),
                    "dividend_yield": info.get('dividendYield'),
                    "debt_to_equity": info.get('debtToEquity'),
                    
                    # Profitability metrics
                    "profit_margins": info.get('profitMargins'),
                    "operating_margins": info.get('operatingMargins'),
                    "roa": info.get('returnOnAssets'),
                    "roe": info.get('returnOnEquity'),
                    
                    # Growth metrics
                    "revenue_growth": info.get('revenueGrowth'),
                    "earnings_growth": info.get('earningsGrowth'),
                    
                    # Valuation metrics
                    "ev_to_revenue": info.get('enterpriseToRevenue'),
                    "ev_to_ebitda": info.get('enterpriseToEbitda'),
                    "price_to_sales": info.get('priceToSalesTrailing12Months'),
                    
                    # Efficiency metrics
                    "inventory_turnover": info.get('inventoryTurnover'),
                    "quick_ratio": info.get('quickRatio'),
                    "current_ratio": info.get('currentRatio'),
                    
                    # Additional metrics
                    "beta": info.get('beta'),
                    "shares_outstanding": info.get('sharesOutstanding'),
                    "float_shares": info.get('floatShares'),
                    "shares_short": info.get('sharesShort'),
                    "peg_ratio": info.get('pegRatio')
                })
                
                # Remove None values
                metrics = {k: v for k, v in metrics.items() if v is not None}
                
            except Exception as e:
                logger.warning(f"Error fetching Yahoo Finance metrics for {symbol}: {e}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error fetching fundamental metrics for {symbol}: {e}")
            return {} 