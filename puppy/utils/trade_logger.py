import pandas as pd
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
from loguru import logger

class TradeLogger:
    """Handles logging of trades to CSV file"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create trades log file if it doesn't exist
        self.trades_file = self.log_dir / "trades.csv"
        if not self.trades_file.exists():
            self._create_trades_file()
            
    def _create_trades_file(self):
        """Create trades log file with headers"""
        columns = [
            "timestamp",
            "action",
            "symbol",
            "quantity",
            "price",
            "value",
            "cash_after_trade",
            "portfolio_value",
            "profit_loss",
            "profit_loss_pct",
            "reason"
        ]
        df = pd.DataFrame(columns=columns)
        df.to_csv(self.trades_file, index=False)
        logger.info(f"Created trades log file at {self.trades_file}")
        
    def log_trade(self, trade_data: Dict[str, Any]):
        """
        Log a trade to CSV file
        
        Args:
            trade_data: Dictionary containing trade details
        """
        try:
            # Read existing trades
            trades_df = pd.read_csv(self.trades_file)
            
            # Create new trade row
            new_trade = pd.DataFrame([trade_data])
            
            # Append new trade
            updated_df = pd.concat([trades_df, new_trade], ignore_index=True)
            
            # Save updated trades
            updated_df.to_csv(self.trades_file, index=False)
            
            logger.debug(f"Logged trade: {trade_data['action']} {trade_data['quantity']} {trade_data['symbol']} @ ₹{trade_data['price']:,.2f}")
            
        except Exception as e:
            logger.error(f"Error logging trade: {str(e)}")
            
    def get_trade_history(self) -> pd.DataFrame:
        """Get all logged trades as DataFrame"""
        try:
            return pd.read_csv(self.trades_file)
        except Exception as e:
            logger.error(f"Error reading trade history: {str(e)}")
            return pd.DataFrame() 