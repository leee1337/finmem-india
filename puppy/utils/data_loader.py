from typing import Dict, Any
import pandas as pd
import yfinance as yf
from loguru import logger
from datetime import datetime

class DataLoader:
    """Loads market data from various sources"""
    
    def __init__(self, market_config: Dict[str, Any]):
        self.config = market_config
        
    def load_data(self) -> pd.DataFrame:
        """
        Load market data for configured symbols
        
        Returns:
            DataFrame with market data
        """
        logger.info(f"Loading data for {len(self.config['symbols'])} symbols...")
        
        # Convert dates to datetime
        start_date = pd.to_datetime(self.config["data_start_date"])
        end_date = pd.to_datetime(self.config["data_end_date"])
        
        # Download data for each symbol
        data_frames = []
        for symbol in self.config["symbols"]:
            try:
                # Download data from Yahoo Finance with adjusted prices
                ticker = yf.Ticker(f"{symbol}.NS")  # Append .NS for Indian stocks
                df = ticker.history(
                    start=start_date,
                    end=end_date,
                    auto_adjust=True  # Get adjusted prices
                )
                
                # Ensure numeric types and handle adjustments
                numeric_columns = ["Open", "High", "Low", "Close", "Volume"]
                for col in numeric_columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                
                # Set proper index
                df = df.reset_index()
                df["Date"] = pd.to_datetime(df["Date"])  # Ensure date is datetime
                df["Symbol"] = symbol  # Keep original symbol without .NS
                
                # Add additional metrics
                df["Daily_Return"] = df["Close"].pct_change()
                df["20d_MA"] = df["Close"].rolling(window=20).mean()
                df["50d_MA"] = df["Close"].rolling(window=50).mean()
                df["RSI"] = self._calculate_rsi(df["Close"])
                df["Volume_MA"] = df["Volume"].rolling(window=20).mean()
                
                data_frames.append(df)
                logger.debug(f"Loaded data for {symbol}")
                
            except Exception as e:
                logger.error(f"Error loading data for {symbol}: {str(e)}")
                continue
                
        if not data_frames:
            raise RuntimeError("No data could be loaded for any symbol")
            
        # Combine all data and set index
        market_data = pd.concat(data_frames)
        market_data = market_data.set_index(["Date", "Symbol"])
        
        # Sort index
        market_data.sort_index(inplace=True)
        
        # Fill any missing values using forward fill
        market_data = market_data.ffill()
        
        logger.info(f"Loaded data with shape: {market_data.shape}")
        return market_data
        
    def _calculate_rsi(self, prices: pd.Series, periods: int = 14) -> pd.Series:
        """Calculate RSI technical indicator"""
        delta = prices.diff()
        
        gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi 