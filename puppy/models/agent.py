from typing import Dict, Any, List
import pandas as pd
from loguru import logger
from ..utils.real_time_data import RealTimeDataManager
from .memory import LayeredMemory
from .llm import GeminiTrader
from .rule_based_trader import RuleBasedTrader
import os

class TradingAgent:
    """Trading agent that makes decisions based on market data, news, and memory"""
    
    def __init__(self, config: Dict[str, Any], chat_config: Dict[str, Any], memory_config: Dict[str, Any]):
        self.config = {
            "agent": config,
            "chat": chat_config,
            "memory": memory_config
        }
        self.last_trade_date = {}  # Track last trade date for each symbol
        self.min_hold_days = 1  # Reduced from 5 to 1 day minimum holding period
        self.real_time_data = RealTimeDataManager()
        
        # Initialize layered memory
        self.memory = LayeredMemory(self.config)
        
        # Initialize traders
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            self.trader = GeminiTrader(api_key, self.config)
        else:
            logger.info("GEMINI_API_KEY not found, using rule-based trader")
            self.trader = RuleBasedTrader(self.config)
        
    def update_memory(self, market_data: Dict[str, Any]):
        """
        Update agent's memory with new market data
        
        Args:
            market_data: Dictionary containing date and market data
        """
        self.memory.add_memory(market_data, "market_data")
        logger.debug("Memory updated with new market data")
    
    def make_decisions(
        self,
        daily_data: pd.DataFrame,
        portfolio_state: Dict[str, Any],
        current_date: pd.Timestamp,
        news: List[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Make trading decisions based on market data, portfolio state, and memory
        
        Args:
            daily_data: DataFrame containing current market data
            portfolio_state: Current portfolio state
            current_date: Current trading date
            news: Optional list of news articles
            
        Returns:
            Dictionary mapping symbols to trading actions
        """
        # Get data for current date
        try:
            current_data = daily_data.xs(current_date, level="Date")
        except KeyError:
            logger.warning(f"No data available for date {current_date}")
            return {}
            
        # Convert current data to dict format
        market_data = {
            "date": current_date,
            "data": []
        }
        
        # Process each symbol's data
        for symbol in current_data.index:
            # Skip if we haven't held the position for minimum days
            if symbol in self.last_trade_date:
                days_since_trade = (current_date - self.last_trade_date[symbol]).days
                if days_since_trade < self.min_hold_days:
                    continue
                    
            row = current_data.loc[symbol]
            current_price = float(row["Close"])
            
            # Handle both Series and scalar values
            def get_value(x):
                if isinstance(x, pd.Series):
                    return float(x.iloc[0])
                return float(x)
                
            def is_valid(x):
                if isinstance(x, pd.Series):
                    return not x.isna().iloc[0]
                return pd.notna(x)
                
            # Convert Series to scalar values
            market_data["data"].append({
                "Symbol": symbol,
                "Open": get_value(row["Open"]),
                "High": get_value(row["High"]),
                "Low": get_value(row["Low"]),
                "Close": current_price,
                "Volume": get_value(row["Volume"]),
                "Daily_Return": (current_price - get_value(row["Close"])) / get_value(row["Close"]),
                "RSI": get_value(row["RSI"]) if is_valid(row["RSI"]) else 50.0,
                "20d_MA": get_value(row["20d_MA"]) if is_valid(row["20d_MA"]) else None,
                "50d_MA": get_value(row["50d_MA"]) if is_valid(row["50d_MA"]) else None,
                "Volume_MA": get_value(row["Volume_MA"]) if is_valid(row["Volume_MA"]) else None
            })
            
        # Update memory
        self.update_memory(market_data)
        
        # Get relevant memories
        market_trend = "neutral"
        if market_data['data'] and market_data['data'][0]['20d_MA'] is not None and market_data['data'][0]['50d_MA'] is not None:
            market_trend = 'bullish' if market_data['data'][0]['20d_MA'] > market_data['data'][0]['50d_MA'] else 'bearish'
            
        query = f"What are the relevant market patterns and events for current conditions? Market trend is {market_trend}"
        relevant_memories = self.memory.retrieve_relevant_memories(query)
        
        # Get trading decisions from trader
        decisions = self.trader.make_decision(
            market_data,
            portfolio_state,
            relevant_memories,
            news or []
        )
        
        # Update last trade dates
        for symbol, decision in decisions.items():
            self.last_trade_date[symbol] = current_date
            
        return decisions 