from typing import Dict, Any
from loguru import logger
import pandas as pd
from .real_time_data import RealTimeDataManager
from .trade_logger import TradeLogger

class Portfolio:
    """Manages trading positions and portfolio state"""
    
    def __init__(self, initial_capital: float, position_size_limit: float):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.position_size_limit = position_size_limit
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.transactions = []
        self.real_time_data = RealTimeDataManager()
        self.trade_logger = TradeLogger()
        
    def get_total_value(self) -> float:
        """Calculate total portfolio value including cash and positions using real-time prices"""
        if not self.positions:
            return self.cash
            
        # Get real-time prices for all positions
        current_prices = self.real_time_data.get_multiple_real_time_prices(
            [symbol for symbol in self.positions.keys()]
        )
        
        position_value = sum(
            pos["quantity"] * (current_prices.get(symbol) or pos["price"])  # Fallback to stored price if real-time unavailable
            for symbol, pos in self.positions.items()
        )
        return self.cash + position_value
        
    def get_state(self) -> Dict[str, Any]:
        """Get current portfolio state with real-time valuations"""
        # Get real-time prices for all positions
        current_prices = self.real_time_data.get_multiple_real_time_prices(
            [symbol for symbol in self.positions.keys()]
        )
        
        # Calculate current position values and returns
        positions_with_value = {}
        for symbol, pos in self.positions.items():
            current_price = current_prices.get(symbol)
            if current_price is None:
                current_price = pos["price"]  # Fallback to stored price
                
            position_value = pos["quantity"] * current_price
            position_return = (current_price - pos["price"]) / pos["price"]
            
            positions_with_value[symbol] = {
                **pos,
                "current_price": current_price,
                "current_value": position_value,
                "return": position_return
            }
        
        total_value = self.get_total_value()
        return {
            "cash": self.cash,
            "positions": positions_with_value,
            "total_value": total_value,
            "returns": (total_value - self.initial_capital) / self.initial_capital
        }
        
    def buy(self, symbol: str, quantity: int, price: float, reason: str = ""):
        """
        Buy a position
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares to buy
            price: Price per share
            reason: Reason for the trade
        """
        try:
            cost = quantity * price
            
            # Check if we have enough cash
            if cost > self.cash:
                logger.warning(f"Not enough cash to buy {quantity} shares of {symbol} at ₹{price:.2f}")
                # Try to buy with available cash
                quantity = int(self.cash / price)
                if quantity < 100:  # Minimum 100 shares
                    logger.warning(f"Not enough cash for minimum position size of {symbol}")
                    return False
                cost = quantity * price
            
            # Check position size limit
            position_value = cost
            portfolio_value = self.get_total_value()
            if position_value / portfolio_value > self.position_size_limit:
                # Adjust quantity to meet limit
                max_quantity = int((portfolio_value * self.position_size_limit) / price)
                if max_quantity < 100:  # Minimum 100 shares
                    logger.warning(f"Position size would be too small for {symbol}")
                    return False
                quantity = max_quantity
                cost = quantity * price
            
            # Execute trade
            self.cash -= cost
            if symbol in self.positions:
                # Average down existing position
                current_pos = self.positions[symbol]
                total_quantity = current_pos["quantity"] + quantity
                total_cost = (current_pos["quantity"] * current_pos["price"]) + cost
                avg_price = total_cost / total_quantity
                self.positions[symbol] = {
                    "quantity": total_quantity,
                    "price": avg_price
                }
            else:
                # Create new position
                self.positions[symbol] = {
                    "quantity": quantity,
                    "price": price
                }
                
            logger.info(f"Bought {quantity} shares of {symbol} at ₹{price:,.2f}")
            self._record_transaction("BUY", symbol, quantity, price, reason)
            return True
            
        except Exception as e:
            logger.error(f"Error executing buy for {symbol}: {str(e)}")
            return False
            
    def sell(self, symbol: str, quantity: int, price: float, reason: str = ""):
        """
        Sell a position
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares to sell
            price: Price per share
            reason: Reason for the trade
        """
        try:
            # Check if market is open
            if not self.real_time_data.is_market_open():
                logger.warning("Cannot execute trade - market is closed")
                return False
                
            if symbol not in self.positions:
                logger.warning(f"No position in {symbol} to sell")
                return False
                
            position = self.positions[symbol]
            if quantity > position["quantity"]:
                quantity = position["quantity"]  # Sell entire position
                
            # Execute trade
            proceeds = quantity * price
            self.cash += proceeds
            
            # Calculate profit/loss
            entry_price = position["price"]
            profit_loss = (price - entry_price) * quantity
            profit_loss_pct = (price - entry_price) / entry_price * 100
            
            # Update position
            remaining_quantity = position["quantity"] - quantity
            if remaining_quantity > 0:
                self.positions[symbol]["quantity"] = remaining_quantity
            else:
                del self.positions[symbol]
                
            logger.info(f"Sold {quantity} shares of {symbol} at ₹{price:,.2f}")
            self._record_transaction("SELL", symbol, quantity, price, reason, profit_loss, profit_loss_pct)
            return True
            
        except Exception as e:
            logger.error(f"Error executing sell for {symbol}: {str(e)}")
            return False
        
    def _record_transaction(
        self,
        action: str,
        symbol: str,
        quantity: int,
        price: float,
        reason: str = "",
        profit_loss: float = 0.0,
        profit_loss_pct: float = 0.0
    ):
        """Record a transaction"""
        timestamp = pd.Timestamp.now()
        value = quantity * price
        portfolio_value = self.get_total_value()
        
        # Record in memory
        self.transactions.append({
            "action": action,
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "value": value,
            "timestamp": timestamp
        })
        
        # Log to CSV
        trade_data = {
            "timestamp": timestamp,
            "action": action,
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "value": value,
            "cash_after_trade": self.cash,
            "portfolio_value": portfolio_value,
            "profit_loss": profit_loss if action == "SELL" else 0.0,
            "profit_loss_pct": profit_loss_pct if action == "SELL" else 0.0,
            "reason": reason
        }
        self.trade_logger.log_trade(trade_data) 