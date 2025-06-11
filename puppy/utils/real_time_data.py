import yfinance as yf
from typing import Dict, Optional, List
from loguru import logger
import pandas as pd
from datetime import datetime, time
import pytz

class RealTimeDataManager:
    """Manages real-time market data for Indian stocks"""
    
    def __init__(self):
        # Indian market trading hours (IST)
        self.ist = pytz.timezone('Asia/Kolkata')
        self.market_open = time(9, 15)  # 9:15 AM IST
        self.market_close = time(15, 30)  # 3:30 PM IST
        
    def is_market_open(self) -> bool:
        """Check if Indian market is currently open"""
        current_time = datetime.now(self.ist).time()
        return self.market_open <= current_time <= self.market_close
        
    def get_real_time_price(self, symbol: str) -> Optional[float]:
        """
        Get real-time price for a symbol
        
        Args:
            symbol: Stock symbol (with or without .NS suffix)
            
        Returns:
            Current price if available, None otherwise
        """
        try:
            # Ensure symbol has .NS suffix
            if not symbol.endswith('.NS'):
                symbol = f"{symbol}.NS"
                
            # Get real-time data
            ticker = yf.Ticker(symbol)
            current_price = ticker.info.get('regularMarketPrice')
            
            if current_price is None:
                logger.warning(f"Could not get real-time price for {symbol}")
                return None
                
            return float(current_price)
            
        except Exception as e:
            logger.error(f"Error fetching real-time price for {symbol}: {str(e)}")
            return None
            
    def get_multiple_real_time_prices(self, symbols: List[str]) -> Dict[str, Optional[float]]:
        """
        Get real-time prices for multiple symbols
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbols to their current prices
        """
        prices = {}
        for symbol in symbols:
            clean_symbol = symbol.replace('.NS', '')
            prices[clean_symbol] = self.get_real_time_price(symbol)
        return prices 