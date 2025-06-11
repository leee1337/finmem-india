import yfinance as yf
from datetime import datetime, timedelta
import random

def get_nifty50_symbols():
    """Get a list of NIFTY 50 symbols"""
    return [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK"
    ]  # Simplified list for testing

def get_mock_price(symbol: str) -> float:
    """Get a mock price for testing"""
    base_prices = {
        "RELIANCE": 2500.0,
        "TCS": 3500.0,
        "HDFCBANK": 1600.0,
        "INFY": 1400.0,
        "ICICIBANK": 950.0,
        "HINDUNILVR": 2700.0,
        "ITC": 420.0,
        "SBIN": 650.0,
        "BHARTIARTL": 850.0,
        "KOTAKBANK": 1750.0
    }
    # Add some random variation
    return base_prices.get(symbol, 1000.0) * (1 + random.uniform(-0.05, 0.05))

def create_sample_portfolio():
    """Create a sample portfolio with some NIFTY 50 stocks"""
    portfolio = {}
    symbols = get_nifty50_symbols()
    
    for symbol in random.sample(symbols, 3):  # Start with 3 random stocks
        current_price = get_mock_price(symbol)
        
        portfolio[symbol] = {
            'quantity': random.randint(10, 100),
            'price': current_price,
            'purchase_date': (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d')
        }
    
    return portfolio

def create_sample_transactions(portfolio):
    """Create sample transactions based on the portfolio"""
    transactions = []
    
    # Add purchase transactions for current portfolio
    for symbol, data in portfolio.items():
        transactions.append({
            'date': data['purchase_date'],
            'symbol': symbol,
            'action': 'BUY',
            'quantity': data['quantity'],
            'price': data['price'],
            'value': data['quantity'] * data['price'],
            'profit_loss': 0
        })
    
    # Add some historical transactions
    symbols = get_nifty50_symbols()
    for _ in range(5):  # Add 5 random historical transactions
        symbol = random.choice(symbols)
        action = random.choice(['BUY', 'SELL'])
        quantity = random.randint(10, 100)
        price = get_mock_price(symbol)
        
        # Generate random date within last 60 days
        random_date = datetime.now() - timedelta(days=random.randint(1, 60))
        # Format date consistently
        date_str = random_date.strftime('%Y-%m-%d')
        
        transactions.append({
            'date': date_str,
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'price': price,
            'value': quantity * price,
            'profit_loss': random.uniform(-5000, 5000) if action == 'SELL' else 0
        })
    
    return sorted(transactions, key=lambda x: x['date'], reverse=True)

def initialize_test_data():
    """Initialize test data for the application"""
    portfolio = create_sample_portfolio()
    transactions = create_sample_transactions(portfolio)
    
    initial_capital = 1000000  # 10 Lakhs
    current_capital = initial_capital
    
    # Adjust capital based on transactions
    for transaction in transactions:
        if transaction['action'] == 'BUY':
            current_capital -= transaction['value']
        else:
            current_capital += transaction['value']
    
    return {
        "user": "Ashutosh",
        "capital": current_capital,
        "initial_capital": initial_capital,
        "portfolio": portfolio,
        "transactions": transactions
    } 