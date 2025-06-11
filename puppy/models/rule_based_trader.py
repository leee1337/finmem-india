from typing import Dict, Any, List
from loguru import logger
import math

class RuleBasedTrader:
    """Simple rule-based trading strategy for backtesting"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    def calculate_position_size(self, portfolio_value: float, current_price: float) -> int:
        """Calculate position size based on portfolio value and risk management"""
        # Use 10% of portfolio per position, with minimum 100 shares
        position_value = portfolio_value * 0.10  # Increased from 5% to 10%
        quantity = math.floor(position_value / current_price)
        return max(100, min(quantity, 2000))  # Increased max shares from 1000 to 2000
        
    def make_decision(
        self,
        market_data: Dict[str, Any],
        portfolio_state: Dict[str, Any],
        memories: List[Dict[str, Any]] = None,
        news: List[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Make trading decisions based on simple technical rules"""
        decisions = {}
        portfolio_value = float(portfolio_state.get("total_value", 0))
        
        for stock_data in market_data["data"]:
            symbol = stock_data["Symbol"]
            current_price = stock_data["Close"]
            rsi = stock_data["RSI"]
            ma_20 = stock_data["20d_MA"]
            ma_50 = stock_data["50d_MA"]
            volume = stock_data["Volume"]
            volume_ma = stock_data["Volume_MA"]
            
            # Skip if we don't have enough data
            if ma_20 is None or ma_50 is None:
                continue
                
            # Check if we already have a position
            has_position = symbol in portfolio_state.get("positions", {})
            
            # Calculate position size
            position_size = self.calculate_position_size(portfolio_value, current_price)
            
            # Volume confirmation
            volume_signal = volume > volume_ma * 1.1 if volume_ma else True  # Reduced volume threshold
            
            # Simple trading rules with more aggressive conditions
            if not has_position:  # No position, look for buy signals
                if ((rsi < 50 and current_price > ma_20) or  # More lenient RSI
                    (current_price > ma_20 and current_price < ma_50 * 1.05) or  # More lenient price target
                    (current_price > ma_20 and rsi < 60 and volume_signal) or  # More lenient entry
                    (current_price > ma_20 and current_price < ma_20 * 1.02)):  # Near-term momentum
                    decisions[symbol] = {
                        "action": "buy",
                        "quantity": position_size,
                        "price": current_price,
                        "reason": "Technical indicators showing buying opportunity"
                    }
            else:  # Have position, look for sell signals
                position = portfolio_state["positions"][symbol]
                entry_price = position["price"]
                profit_pct = (current_price - entry_price) / entry_price
                
                if (rsi > 70 or  # Overbought
                    current_price < ma_20 or  # Below short-term MA
                    current_price > ma_50 * 1.08 or  # Higher profit target
                    profit_pct < -0.015 or  # Tighter stop loss (1.5%)
                    profit_pct > 0.02):  # Lower take profit (2%)
                    decisions[symbol] = {
                        "action": "sell",
                        "quantity": position["quantity"],
                        "price": current_price,
                        "reason": "Exit signal triggered based on technical indicators or profit targets"
                    }
                    
        return decisions 