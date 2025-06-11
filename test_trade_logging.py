from puppy.utils.trade_logger import TradeLogger
from datetime import datetime

def test_trade_logging():
    # Initialize trade logger
    logger = TradeLogger(log_dir="logs")
    
    # Create a sample trade
    trade_data = {
        "timestamp": datetime.now(),
        "action": "BUY",
        "symbol": "RELIANCE",
        "quantity": 10,
        "price": 2500.50,
        "value": 25005.00,
        "cash_after_trade": 74995.00,
        "portfolio_value": 100000.00,
        "profit_loss": 0.0,
        "profit_loss_pct": 0.0,
        "reason": "Test trade"
    }
    
    # Log the trade
    logger.log_trade(trade_data)
    
    # Read back the trade history
    history = logger.get_trade_history()
    print("\nTrade history:")
    print(history)

if __name__ == "__main__":
    test_trade_logging() 