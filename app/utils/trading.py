from typing import Dict, Any, List
import random
from datetime import datetime, timedelta
import json
from pathlib import Path
import yfinance as yf
import pandas as pd
import numpy as np

class TradingSimulator:
    def __init__(self, config: Dict[str, Any]):
        self.user = config['user']
        self.initial_capital = float(config['initial_capital'])
        self.capital = self.initial_capital
        self.risk_profile = config['risk_profile']
        self.portfolio: Dict[str, Dict[str, Any]] = {}
        self.transactions: List[Dict[str, Any]] = []
        self.last_update = None
        self.nifty50_symbols = self._get_nifty50_symbols()
        self.stock_prices = self._initialize_stock_prices()
        self.volatility = {sym: random.uniform(0.01, 0.03) for sym in self.nifty50_symbols}
        self.trade_probability = self._get_trade_probability()
        self.last_trade_time = datetime.now()
        self.min_trade_interval = timedelta(seconds=10)  # Minimum time between trades
        
        # Load existing state if available
        self._load_state()
    
    def _get_nifty50_symbols(self) -> List[str]:
        """Get list of Nifty 50 symbols"""
        # For test mode, use a subset of major Indian stocks
        return [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
            "HINDUNILVR", "HDFC", "SBIN", "BHARTIARTL", "ITC",
            "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI"
        ]
    
    def _initialize_stock_prices(self) -> Dict[str, float]:
        """Initialize stock prices with realistic values"""
        prices = {}
        for symbol in self.nifty50_symbols:
            # Generate realistic initial prices
            if symbol in ["RELIANCE", "TCS"]:
                prices[symbol] = random.uniform(2000, 3000)
            elif symbol in ["HDFCBANK", "INFY", "ICICIBANK"]:
                prices[symbol] = random.uniform(1000, 2000)
            else:
                prices[symbol] = random.uniform(300, 1000)
        return prices
    
    def _get_trade_probability(self) -> float:
        """Get trade probability based on risk profile"""
        return {
            "Risk-Averse": 0.4,
            "Balanced": 0.6,
            "Risk-Seeking": 0.8
        }.get(self.risk_profile, 0.5)
    
    def _update_prices(self):
        """Update stock prices with realistic movements"""
        for symbol in self.stock_prices:
            # Generate realistic price movement
            change_pct = np.random.normal(0, self.volatility[symbol])
            self.stock_prices[symbol] *= (1 + change_pct)
            
            # Update portfolio values
            if symbol in self.portfolio:
                self.portfolio[symbol]['current_price'] = self.stock_prices[symbol]
                self.portfolio[symbol]['market_value'] = (
                    self.portfolio[symbol]['quantity'] * self.stock_prices[symbol]
                )
                self.portfolio[symbol]['profit_loss'] = (
                    self.portfolio[symbol]['market_value'] -
                    (self.portfolio[symbol]['quantity'] * self.portfolio[symbol]['avg_price'])
                )
    
    def _should_trade(self) -> bool:
        """Determine if a trade should be made"""
        if datetime.now() - self.last_trade_time < self.min_trade_interval:
            return False
        return random.random() < self.trade_probability
    
    def _generate_trade(self):
        """Generate a realistic trade"""
        # Select action (buy/sell)
        if not self.portfolio:
            action = "BUY"  # Force buy if portfolio is empty
        elif len(self.portfolio) >= 10:
            action = "SELL"  # Force sell if portfolio is too large
        else:
            action = random.choice(["BUY", "SELL"])
        
        if action == "SELL" and not self.portfolio:
            return None  # Can't sell if nothing in portfolio
        
        # Select symbol
        if action == "BUY":
            available_symbols = [s for s in self.nifty50_symbols if s not in self.portfolio]
            if not available_symbols:
                return None
            symbol = random.choice(available_symbols)
        else:
            symbol = random.choice(list(self.portfolio.keys()))
        
        current_price = self.stock_prices[symbol]
        
        # Calculate quantity based on available capital and position size
        if action == "BUY":
            max_capital = min(self.capital, self.initial_capital * 0.2)  # Max 20% of initial capital per position
            max_quantity = int(max_capital / current_price)
            quantity = random.randint(1, max_quantity) if max_quantity > 0 else 0
        else:
            max_quantity = self.portfolio[symbol]['quantity']
            quantity = random.randint(1, max_quantity)
        
        if quantity == 0:
            return None
        
        value = quantity * current_price
        
        # Execute trade
        if action == "BUY":
            if value > self.capital:
                return None
            
            self.capital -= value
            
            if symbol not in self.portfolio:
                self.portfolio[symbol] = {
                    'symbol': symbol,
                    'quantity': quantity,
                    'avg_price': current_price,
                    'current_price': current_price,
                    'market_value': value,
                    'profit_loss': 0
                }
            else:
                total_quantity = self.portfolio[symbol]['quantity'] + quantity
                total_value = (
                    self.portfolio[symbol]['quantity'] * self.portfolio[symbol]['avg_price'] +
                    quantity * current_price
                )
                self.portfolio[symbol]['quantity'] = total_quantity
                self.portfolio[symbol]['avg_price'] = total_value / total_quantity
                self.portfolio[symbol]['current_price'] = current_price
                self.portfolio[symbol]['market_value'] = total_quantity * current_price
        
        else:  # SELL
            sale_value = quantity * current_price
            self.capital += sale_value
            
            profit_loss = (current_price - self.portfolio[symbol]['avg_price']) * quantity
            
            remaining_quantity = self.portfolio[symbol]['quantity'] - quantity
            if remaining_quantity == 0:
                del self.portfolio[symbol]
            else:
                self.portfolio[symbol]['quantity'] = remaining_quantity
                self.portfolio[symbol]['market_value'] = remaining_quantity * current_price
        
        # Record transaction
        transaction = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'price': current_price,
            'value': value,
            'profit_loss': profit_loss if action == "SELL" else 0
        }
        
        self.transactions.append(transaction)
        self.last_trade_time = datetime.now()
        
        # Save state after each trade
        self._save_state()
        
        return transaction
    
    def update(self):
        """Update simulation state"""
        self._update_prices()
        
        # Generate trades more frequently
        if self._should_trade():
            trade = self._generate_trade()
            if trade:
                print(f"Trade executed: {trade['action']} {trade['quantity']} {trade['symbol']} @ {trade['price']}")
        
        self.last_update = datetime.now()
        
        # Save state after each update
        self._save_state()
    
    def get_state(self) -> Dict[str, Any]:
        """Get current simulation state"""
        total_value = self.capital + sum(pos['market_value'] for pos in self.portfolio.values())
        total_pl = total_value - self.initial_capital
        
        return {
            'user': self.user,
            'capital': self.capital,
            'initial_capital': self.initial_capital,
            'total_value': total_value,
            'total_pl': total_pl,
            'pl_pct': (total_pl / self.initial_capital) * 100 if self.initial_capital > 0 else 0,
            'portfolio': self.portfolio,
            'transactions': self.transactions,
            'risk_profile': self.risk_profile,
            'last_update': self.last_update
        }
    
    def _save_state(self):
        """Save current state to file"""
        state = self.get_state()
        state_file = Path("data/trading_state.json")
        state_file.parent.mkdir(exist_ok=True)
        
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
    
    def _load_state(self):
        """Load state from file"""
        state_file = Path("data/trading_state.json")
        if state_file.exists():
            with open(state_file, "r") as f:
                state = json.load(f)
            
            self.capital = state.get('capital', self.initial_capital)
            self.portfolio = state.get('portfolio', {})
            self.transactions = state.get('transactions', [])
            self.last_update = datetime.now()
    
    def reset_capital(self, new_capital: float):
        """Reset capital to new value"""
        self.initial_capital = new_capital
        self.capital = new_capital
        self.portfolio.clear()
        self.transactions.clear()
        self.last_update = datetime.now()
        self._save_state() 