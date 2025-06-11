"""
Indian Stock Market Trading System with Layered Memory Architecture
Based on FinMem concept for Nifty 50 stocks with Gemini 2.0 Flash integration
"""

import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import json
import sqlite3
from datetime import datetime, timedelta
import ta
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import logging
import google.generativeai as genai
from textblob import TextBlob
import time
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Nifty 50 stock symbols with .NS suffix for Yahoo Finance
NIFTY_50_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "ASIANPAINT.NS",
    "MARUTI.NS", "BAJFINANCE.NS", "LT.NS", "AXISBANK.NS", "HCLTECH.NS",
    "WIPRO.NS", "ULTRACEMCO.NS", "ONGC.NS", "TITAN.NS", "SUNPHARMA.NS",
    "POWERGRID.NS", "NTPC.NS", "NESTLEIND.NS", "KOTAKBANK.NS", "BAJAJFINSV.NS",
    "M&M.NS", "TECHM.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "INDUSINDBK.NS",
    "ADANIENT.NS", "HDFCLIFE.NS", "SBILIFE.NS", "BPCL.NS", "GRASIM.NS",
    "HINDALCO.NS", "COALINDIA.NS", "HEROMOTOCO.NS", "CIPLA.NS", "DRREDDY.NS",
    "EICHERMOT.NS", "UPL.NS", "APOLLOHOSP.NS", "DIVISLAB.NS", "BRITANNIA.NS",
    "JSWSTEEL.NS", "TATACONSUM.NS", "BAJAJ-AUTO.NS", "ADANIPORTS.NS", "LTIM.NS"
]

@dataclass
class Trade:
    """Trade record structure"""
    timestamp: datetime
    symbol: str
    action: str  # BUY/SELL
    quantity: int
    price: float
    amount: float
    reason: str
    technical_indicators: Dict[str, Any]
    news_sentiment: float
    portfolio_value: float
    cash_balance: float
    
@dataclass
class MemoryRecord:
    """Memory record for layered memory system"""
    timestamp: datetime
    symbol: str
    data_type: str  # PRICE, NEWS, TECHNICAL, TRADE
    content: Dict[str, Any]
    importance_score: float
    embedding: Optional[List[float]] = None

class DatabaseManager:
    """Handles all database operations"""
    
    def __init__(self, db_path: str = "trading_system.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                action TEXT,
                quantity INTEGER,
                price REAL,
                amount REAL,
                reason TEXT,
                technical_indicators TEXT,
                news_sentiment REAL,
                portfolio_value REAL,
                cash_balance REAL
            )
        """)
        
        # Long-term memory table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS long_term_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                data_type TEXT,
                content TEXT,
                importance_score REAL,
                embedding TEXT
            )
        """)
        
        # Short-term memory table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS short_term_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                data_type TEXT,
                content TEXT,
                importance_score REAL,
                embedding TEXT,
                created_at TEXT
            )
        """)
        
        # Portfolio table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                symbol TEXT PRIMARY KEY,
                quantity INTEGER,
                avg_price REAL,
                current_value REAL,
                last_updated TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_trade(self, trade: Trade):
        """Save trade to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Convert technical indicators to JSON-serializable format
        tech_indicators = {}
        for key, value in trade.technical_indicators.items():
            if isinstance(value, (np.int64, np.int32)):
                tech_indicators[key] = int(value)
            elif isinstance(value, (np.float64, np.float32)):
                tech_indicators[key] = float(value)
            else:
                tech_indicators[key] = value
        
        cursor.execute("""
            INSERT INTO trades (timestamp, symbol, action, quantity, price, amount, 
                              reason, technical_indicators, news_sentiment, 
                              portfolio_value, cash_balance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.timestamp.isoformat(),
            trade.symbol,
            trade.action,
            trade.quantity,
            trade.price,
            trade.amount,
            trade.reason,
            json.dumps(tech_indicators),
            trade.news_sentiment,
            trade.portfolio_value,
            trade.cash_balance
        ))
        
        conn.commit()
        conn.close()
    
    def save_memory(self, memory: MemoryRecord, memory_type: str = "long_term"):
        """Save memory record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        table_name = f"{memory_type}_memory"
        
        # Convert content to JSON-serializable format
        content = self._convert_to_json_serializable(memory.content)
        
        if memory_type == "short_term":
            cursor.execute(f"""
                INSERT INTO {table_name} (timestamp, symbol, data_type, content, 
                                        importance_score, embedding, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.timestamp.isoformat(),
                memory.symbol,
                memory.data_type,
                json.dumps(content),
                memory.importance_score,
                json.dumps(memory.embedding) if memory.embedding else None,
                datetime.now().isoformat()
            ))
        else:
            cursor.execute(f"""
                INSERT INTO {table_name} (timestamp, symbol, data_type, content, 
                                        importance_score, embedding)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                memory.timestamp.isoformat(),
                memory.symbol,
                memory.data_type,
                json.dumps(content),
                memory.importance_score,
                json.dumps(memory.embedding) if memory.embedding else None
            ))
        
        conn.commit()
        conn.close()
    
    def _convert_to_json_serializable(self, obj):
        """Convert numpy types to JSON serializable types"""
        if isinstance(obj, dict):
            return {key: self._convert_to_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_json_serializable(item) for item in obj]
        elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32, np.float16)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj

class DataCollector:
    """Collects historical and real-time data"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_historical_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """Get historical stock data"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            return data
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> float:
        """Get current stock price"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            return data['Close'].iloc[-1] if not data.empty else 0.0
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
            return 0.0
    
    def scrape_news_moneycontrol(self, symbol: str) -> List[Dict[str, Any]]:
        """Scrape news from MoneyControl"""
        try:
            # Convert symbol for MoneyControl URL
            clean_symbol = symbol.replace('.NS', '').lower()
            url = f"https://www.moneycontrol.com/news/tags/{clean_symbol}.html"
            
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            news_items = []
            articles = soup.find_all('div', class_='news_boxnew')[:5]  # Get top 5 news
            
            for article in articles:
                try:
                    title_elem = article.find('h2') or article.find('h3')
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    
                    summary_elem = article.find('p')
                    summary = summary_elem.get_text(strip=True) if summary_elem else ""
                    
                    if title:
                        news_items.append({
                            'title': title,
                            'summary': summary,
                            'source': 'MoneyControl',
                            'timestamp': datetime.now()
                        })
                except:
                    continue
            
            return news_items
        except Exception as e:
            logger.error(f"Error scraping MoneyControl for {symbol}: {e}")
            return []
    
    def scrape_economic_times(self, symbol: str) -> List[Dict[str, Any]]:
        """Scrape news from Economic Times"""
        try:
            clean_symbol = symbol.replace('.NS', '').lower()
            url = f"https://economictimes.indiatimes.com/topic/{clean_symbol}"
            
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            news_items = []
            articles = soup.find_all('div', class_='eachStory')[:3]
            
            for article in articles:
                try:
                    title_elem = article.find('h3') or article.find('h2')
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    
                    summary_elem = article.find('p')
                    summary = summary_elem.get_text(strip=True) if summary_elem else ""
                    
                    if title:
                        news_items.append({
                            'title': title,
                            'summary': summary,
                            'source': 'Economic Times',
                            'timestamp': datetime.now()
                        })
                except:
                    continue
            
            return news_items
        except Exception as e:
            logger.error(f"Error scraping Economic Times for {symbol}: {e}")
            return []

class TechnicalAnalyzer:
    """Performs technical analysis on stock data"""
    
    def calculate_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate technical indicators"""
        if data.empty or len(data) < 50:
            return {}
        
        try:
            indicators = {}
            
            # Moving Averages
            indicators['sma_20'] = float(ta.trend.sma_indicator(data['Close'], window=20).iloc[-1])
            indicators['sma_50'] = float(ta.trend.sma_indicator(data['Close'], window=50).iloc[-1])
            indicators['ema_12'] = float(ta.trend.ema_indicator(data['Close'], window=12).iloc[-1])
            indicators['ema_26'] = float(ta.trend.ema_indicator(data['Close'], window=26).iloc[-1])
            
            # RSI
            indicators['rsi'] = float(ta.momentum.rsi(data['Close'], window=14).iloc[-1])
            
            # MACD
            macd_line = ta.trend.macd(data['Close'])
            macd_signal = ta.trend.macd_signal(data['Close'])
            indicators['macd'] = float(macd_line.iloc[-1])
            indicators['macd_signal'] = float(macd_signal.iloc[-1])
            indicators['macd_histogram'] = float((macd_line - macd_signal).iloc[-1])
            
            # Bollinger Bands
            bb_high = ta.volatility.bollinger_hband(data['Close'])
            bb_low = ta.volatility.bollinger_lband(data['Close'])
            bb_mid = ta.volatility.bollinger_mavg(data['Close'])
            indicators['bb_upper'] = float(bb_high.iloc[-1])
            indicators['bb_lower'] = float(bb_low.iloc[-1])
            indicators['bb_middle'] = float(bb_mid.iloc[-1])
            
            # Support and Resistance
            recent_data = data.tail(20)
            indicators['support'] = float(recent_data['Low'].min())
            indicators['resistance'] = float(recent_data['High'].max())
            
            # Volume indicators
            indicators['volume_sma'] = float(data['Volume'].rolling(window=20).mean().iloc[-1])
            indicators['current_volume'] = int(data['Volume'].iloc[-1])
            
            # Price metrics
            indicators['current_price'] = float(data['Close'].iloc[-1])
            indicators['price_change_1d'] = float((data['Close'].iloc[-1] - data['Close'].iloc[-2]) / data['Close'].iloc[-2] * 100)
            indicators['price_change_5d'] = float((data['Close'].iloc[-1] - data['Close'].iloc[-6]) / data['Close'].iloc[-6] * 100)
            
            # Handle any NaN values
            for key, value in indicators.items():
                if pd.isna(value):
                    indicators[key] = 0.0 if isinstance(value, float) else 0
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            return {}

class NewsAnalyzer:
    """Analyzes news sentiment"""
    
    def analyze_sentiment(self, news_items: List[Dict[str, Any]]) -> float:
        """Analyze sentiment of news items"""
        if not news_items:
            return 0.0
        
        total_sentiment = 0.0
        count = 0
        
        for item in news_items:
            text = f"{item.get('title', '')} {item.get('summary', '')}"
            if text.strip():
                blob = TextBlob(text)
                sentiment = blob.sentiment.polarity
                total_sentiment += sentiment
                count += 1
        
        return total_sentiment / count if count > 0 else 0.0

class LayeredMemorySystem:
    """Implements layered memory architecture"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.short_term_capacity = 100  # Max items in short-term memory
        self.importance_threshold = 0.7  # Threshold for long-term memory
    
    def add_memory(self, memory: MemoryRecord):
        """Add memory to appropriate layer"""
        if memory.importance_score >= self.importance_threshold:
            # Add to long-term memory
            self.db_manager.save_memory(memory, "long_term")
            logger.info(f"Added to long-term memory: {memory.symbol} - {memory.data_type}")
        
        # Always add to short-term memory
        self.db_manager.save_memory(memory, "short_term")
        self._cleanup_short_term_memory()
    
    def _cleanup_short_term_memory(self):
        """Remove old items from short-term memory"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Keep only recent items
        cursor.execute("""
            DELETE FROM short_term_memory 
            WHERE id NOT IN (
                SELECT id FROM short_term_memory 
                ORDER BY created_at DESC 
                LIMIT ?
            )
        """, (self.short_term_capacity,))
        
        conn.commit()
        conn.close()
    
    def calculate_importance_score(self, data_type: str, content: Dict[str, Any]) -> float:
        """Calculate importance score for memory item"""
        base_score = 0.5
        
        if data_type == "PRICE":
            # Price changes are important
            price_change = abs(content.get('price_change_1d', 0))
            base_score += min(price_change / 10, 0.4)
        
        elif data_type == "NEWS":
            # News sentiment extremes are important
            sentiment = abs(content.get('sentiment', 0))
            base_score += min(sentiment, 0.4)
        
        elif data_type == "TECHNICAL":
            # Technical signals are important
            rsi = content.get('rsi', 50)
            if rsi > 70 or rsi < 30:  # Overbought/oversold
                base_score += 0.3
        
        elif data_type == "TRADE":
            # All trades are important
            base_score = 0.8
        
        return min(base_score, 1.0)

class GeminiAnalyzer:
    """Uses Gemini 2.0 Flash for trading decisions"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def make_trading_decision(self, symbol: str, technical_data: Dict[str, Any], 
                            news_sentiment: float, memory_context: str) -> Dict[str, Any]:
        """Make trading decision using Gemini"""
        
        prompt = f"""
        As an expert stock trader, analyze the following data for {symbol} and make a trading decision:

        TECHNICAL INDICATORS:
        - Current Price: ₹{technical_data.get('current_price', 0):.2f}
        - RSI: {technical_data.get('rsi', 0):.2f}
        - MACD: {technical_data.get('macd', 0):.4f}
        - MACD Signal: {technical_data.get('macd_signal', 0):.4f}
        - SMA 20: ₹{technical_data.get('sma_20', 0):.2f}
        - SMA 50: ₹{technical_data.get('sma_50', 0):.2f}
        - Bollinger Upper: ₹{technical_data.get('bb_upper', 0):.2f}
        - Bollinger Lower: ₹{technical_data.get('bb_lower', 0):.2f}
        - Support: ₹{technical_data.get('support', 0):.2f}
        - Resistance: ₹{technical_data.get('resistance', 0):.2f}
        - 1-day price change: {technical_data.get('price_change_1d', 0):.2f}%
        - 5-day price change: {technical_data.get('price_change_5d', 0):.2f}%

        NEWS SENTIMENT: {news_sentiment:.2f} (range: -1 to 1, where -1 is very negative, 1 is very positive)

        MEMORY CONTEXT:
        {memory_context}

        Please provide your trading decision in the following JSON format:
        {{
            "action": "BUY/SELL/HOLD",
            "confidence": 0.0-1.0,
            "reasoning": "Detailed explanation of the decision",
            "risk_level": "LOW/MEDIUM/HIGH",
            "target_price": 0.0,
            "stop_loss": 0.0
        }}

        Consider technical analysis patterns, news sentiment, market conditions, and risk management.
        """
        
        try:
            response = self.model.generate_content(prompt)
            decision_text = response.text
            print(response.text)

            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', decision_text, re.DOTALL)
            if json_match:
                raw_json = json_match.group()

                # 🧼 Clean control characters from raw JSON string
                cleaned_json = re.sub(r'[\x00-\x1F\x7F]', '', raw_json)

                try:
                    decision = json.loads(cleaned_json)
                    return decision
                except json.JSONDecodeError as decode_err:
                    logger.error(f"JSON decoding failed after cleaning: {decode_err}")

            # Fallback if JSON match fails or decoding fails
            return {
                "action": "HOLD",
                "confidence": 0.5,
                "reasoning": "Unable to parse AI decision",
                "risk_level": "MEDIUM",
                "target_price": technical_data.get('current_price', 0),
                "stop_loss": technical_data.get('current_price', 0) * 0.95
            }

        except Exception as e:
            logger.error(f"Error getting Gemini decision: {e}")
            return {
                "action": "HOLD",
                "confidence": 0.5,
                "reasoning": f"AI analysis failed: {str(e)}",
                "risk_level": "HIGH",
                "target_price": technical_data.get('current_price', 0),
                "stop_loss": technical_data.get('current_price', 0) * 0.95
            }

class PaperTradingEngine:
    """Paper trading engine with portfolio management"""
    
    def __init__(self, initial_capital: float = 1000000.0):
        self.initial_capital = initial_capital
        self.cash_balance = initial_capital
        self.portfolio = {}  # {symbol: {'quantity': int, 'avg_price': float}}
        self.position_size_pct = 0.05  # 5% of portfolio per position
        self.max_positions = 10
    
    def get_portfolio_value(self, data_collector: DataCollector) -> float:
        """Calculate total portfolio value"""
        total_value = self.cash_balance
        
        for symbol, position in self.portfolio.items():
            current_price = data_collector.get_current_price(symbol)
            total_value += position['quantity'] * current_price
        
        return total_value
    
    def calculate_position_size(self, price: float, portfolio_value: float) -> int:
        """Calculate position size based on risk management"""
        position_value = portfolio_value * self.position_size_pct
        quantity = int(position_value / price)
        return max(1, quantity)  # At least 1 share
    
    def can_buy(self, symbol: str, price: float, quantity: int) -> bool:
        """Check if buy order is possible"""
        required_cash = price * quantity
        return (self.cash_balance >= required_cash and 
                len(self.portfolio) < self.max_positions)
    
    def can_sell(self, symbol: str, quantity: int) -> bool:
        """Check if sell order is possible"""
        return (symbol in self.portfolio and 
                self.portfolio[symbol]['quantity'] >= quantity)
    
    def execute_buy(self, symbol: str, price: float, quantity: int) -> bool:
        """Execute buy order"""
        if not self.can_buy(symbol, price, quantity):
            return False
        
        cost = price * quantity
        self.cash_balance -= cost
        
        if symbol in self.portfolio:
            # Update average price
            current_qty = self.portfolio[symbol]['quantity']
            current_avg = self.portfolio[symbol]['avg_price']
            new_qty = current_qty + quantity
            new_avg = ((current_qty * current_avg) + (quantity * price)) / new_qty
            
            self.portfolio[symbol] = {
                'quantity': new_qty,
                'avg_price': new_avg
            }
        else:
            self.portfolio[symbol] = {
                'quantity': quantity,
                'avg_price': price
            }
        
        return True
    
    def execute_sell(self, symbol: str, price: float, quantity: int) -> bool:
        """Execute sell order"""
        if not self.can_sell(symbol, quantity):
            return False
        
        proceeds = price * quantity
        self.cash_balance += proceeds
        
        self.portfolio[symbol]['quantity'] -= quantity
        
        # Remove from portfolio if quantity becomes 0
        if self.portfolio[symbol]['quantity'] == 0:
            del self.portfolio[symbol]
        
        return True

class TradingSystem:
    """Main trading system orchestrator"""
    
    def __init__(self, gemini_api_key: str):
        self.db_manager = DatabaseManager()
        self.data_collector = DataCollector()
        self.technical_analyzer = TechnicalAnalyzer()
        self.news_analyzer = NewsAnalyzer()
        self.memory_system = LayeredMemorySystem(self.db_manager)
        self.gemini_analyzer = GeminiAnalyzer(gemini_api_key)
        self.trading_engine = PaperTradingEngine()
        
        logger.info("Trading system initialized")
    
    def process_stock(self, symbol: str):
        """Process a single stock for trading decision"""
        logger.info(f"Processing {symbol}")
        
        # Get historical data
        historical_data = self.data_collector.get_historical_data(symbol)
        if historical_data.empty:
            logger.warning(f"No data available for {symbol}")
            return
        
        # Calculate technical indicators
        technical_indicators = self.technical_analyzer.calculate_indicators(historical_data)
        if not technical_indicators:
            logger.warning(f"Could not calculate indicators for {symbol}")
            return
        
        # Get news and analyze sentiment
        news_items = []
        news_items.extend(self.data_collector.scrape_news_moneycontrol(symbol))
        news_items.extend(self.data_collector.scrape_economic_times(symbol))
        
        news_sentiment = self.news_analyzer.analyze_sentiment(news_items)
        
        # Store in memory
        self._store_memories(symbol, technical_indicators, news_items, news_sentiment)
        
        # Get memory context for AI
        memory_context = self._get_memory_context(symbol)
        
        # Make trading decision using Gemini
        decision = self.gemini_analyzer.make_trading_decision(
            symbol, technical_indicators, news_sentiment, memory_context
        )
        
        # Execute trade if decision is BUY or SELL
        self._execute_trade_decision(symbol, decision, technical_indicators, news_sentiment)
        
        # Add delay to avoid rate limiting
        time.sleep(1)
    
    def _store_memories(self, symbol: str, technical_indicators: Dict[str, Any], 
                       news_items: List[Dict[str, Any]], news_sentiment: float):
        """Store data in memory system"""
        timestamp = datetime.now()
        
        # Store technical data
        tech_memory = MemoryRecord(
            timestamp=timestamp,
            symbol=symbol,
            data_type="TECHNICAL",
            content=technical_indicators,
            importance_score=self.memory_system.calculate_importance_score("TECHNICAL", technical_indicators)
        )
        self.memory_system.add_memory(tech_memory)
        
        # Store news data
        if news_items:
            news_content = {
                'news_items': news_items,
                'sentiment': news_sentiment,
                'news_count': len(news_items)
            }
            news_memory = MemoryRecord(
                timestamp=timestamp,
                symbol=symbol,
                data_type="NEWS",
                content=news_content,
                importance_score=self.memory_system.calculate_importance_score("NEWS", news_content)
            )
            self.memory_system.add_memory(news_memory)
    
    def _get_memory_context(self, symbol: str) -> str:
        """Get relevant memory context for trading decision"""
        # This is a simplified version - in production, you'd use embeddings and similarity search
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Get recent memories for this symbol
        cursor.execute("""
            SELECT data_type, content, importance_score 
            FROM short_term_memory 
            WHERE symbol = ? 
            ORDER BY timestamp DESC 
            LIMIT 5
        """, (symbol,))
        
        memories = cursor.fetchall()
        conn.close()
        
        context = f"Recent activity for {symbol}:\n"
        for data_type, content_json, importance in memories:
            try:
                content = json.loads(content_json)
                if data_type == "TECHNICAL":
                    context += f"- Technical: RSI={content.get('rsi', 0):.1f}, Price Change 1d={content.get('price_change_1d', 0):.2f}%\n"
                elif data_type == "NEWS":
                    context += f"- News: {content.get('news_count', 0)} articles, sentiment={content.get('sentiment', 0):.2f}\n"
            except:
                continue
        
        return context
    
    def _execute_trade_decision(self, symbol: str, decision: Dict[str, Any], 
                              technical_indicators: Dict[str, Any], news_sentiment: float):
        """Execute trading decision"""
        action = decision.get('action', 'HOLD')
        current_price = technical_indicators.get('current_price', 0)
        
        if action == 'HOLD' or current_price == 0:
            return
        
        portfolio_value = self.trading_engine.get_portfolio_value(self.data_collector)
        
        if action == 'BUY':
            quantity = self.trading_engine.calculate_position_size(current_price, portfolio_value)
            
            if self.trading_engine.execute_buy(symbol, current_price, quantity):
                trade = Trade(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    action='BUY',
                    quantity=quantity,
                    price=current_price,
                    amount=current_price * quantity,
                    reason=decision.get('reasoning', ''),
                    technical_indicators=technical_indicators,
                    news_sentiment=news_sentiment,
                    portfolio_value=portfolio_value,
                    cash_balance=self.trading_engine.cash_balance
                )
                
                self.db_manager.save_trade(trade)
                logger.info(f"BUY executed: {symbol} x{quantity} @ ₹{current_price:.2f}")
        
        elif action == 'SELL' and symbol in self.trading_engine.portfolio:
            # Sell all holdings for this stock
            quantity = self.trading_engine.portfolio[symbol]['quantity']
            
            if self.trading_engine.execute_sell(symbol, current_price, quantity):
                pnl = (current_price - self.trading_engine.portfolio.get(symbol, {}).get('avg_price', current_price)) * quantity
                
                trade = Trade(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    action='SELL',
                    quantity=quantity,
                    price=current_price,
                    amount=current_price * quantity,
                    reason=f"{decision.get('reasoning', '')} | PnL: ₹{pnl:.2f}",
                    technical_indicators=technical_indicators,
                    news_sentiment=news_sentiment,
                    portfolio_value=portfolio_value,
                    cash_balance=self.trading_engine.cash_balance
                )
                
                self.db_manager.save_trade(trade)
                logger.info(f"SELL executed: {symbol} x{quantity} @ ₹{current_price:.2f} | PnL: ₹{pnl:.2f}")
        
        # Store trade decision in memory
        trade_memory = MemoryRecord(
            timestamp=datetime.now(),
            symbol=symbol,
            data_type="TRADE",
            content={
                'action': action,
                'price': current_price,
                'decision': decision,
                'portfolio_value': portfolio_value
            },
            importance_score=0.8  # Trades are always important
        )
        self.memory_system.add_memory(trade_memory)
    
    def run_trading_cycle(self):
        """Run one complete trading cycle for all Nifty 50 stocks"""
        logger.info("Starting trading cycle")
        
        # Shuffle symbols to avoid patterns
        symbols = NIFTY_50_SYMBOLS.copy()
        random.shuffle(symbols)
        
        for symbol in symbols:
            try:
                self.process_stock(symbol)
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue
        
        # Log portfolio status
        portfolio_value = self.trading_engine.get_portfolio_value(self.data_collector)
        logger.info(f"Trading cycle completed. Portfolio value: ₹{portfolio_value:,.2f}")
        logger.info(f"Cash balance: ₹{self.trading_engine.cash_balance:,.2f}")
        logger.info(f"Active positions: {len(self.trading_engine.portfolio)}")
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get current portfolio summary"""
        portfolio_value = self.trading_engine.get_portfolio_value(self.data_collector)
        total_return = portfolio_value - self.trading_engine.initial_capital
        return_pct = (total_return / self.trading_engine.initial_capital) * 100
        
        return {
            'initial_capital': self.trading_engine.initial_capital,
            'current_value': portfolio_value,
            'cash_balance': self.trading_engine.cash_balance,
            'total_return': total_return,
            'return_percentage': return_pct,
            'active_positions': len(self.trading_engine.portfolio),
            'positions': dict(self.trading_engine.portfolio)
        }
    
    def get_trade_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trade history"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM trades 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        trades = []
        columns = [description[0] for description in cursor.description]
        
        for row in cursor.fetchall():
            trade_dict = dict(zip(columns, row))
            trades.append(trade_dict)
        
        conn.close()
        return trades

class TradingReporter:
    """Generates trading reports and analytics"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def generate_daily_report(self) -> str:
        """Generate daily trading report"""
        conn = sqlite3.connect(self.db_manager.db_path)
        
        # Get today's trades
        today = datetime.now().date()
        trades_df = pd.read_sql_query("""
            SELECT * FROM trades 
            WHERE date(timestamp) = ?
            ORDER BY timestamp DESC
        """, conn, params=(today.isoformat(),))
        
        if trades_df.empty:
            return "No trades executed today."
        
        # Calculate metrics
        buy_trades = trades_df[trades_df['action'] == 'BUY']
        sell_trades = trades_df[trades_df['action'] == 'SELL']
        
        total_bought = buy_trades['amount'].sum() if not buy_trades.empty else 0
        total_sold = sell_trades['amount'].sum() if not sell_trades.empty else 0
        
        report = f"""
=== DAILY TRADING REPORT - {today} ===

SUMMARY:
- Total Trades: {len(trades_df)}
- Buy Orders: {len(buy_trades)}
- Sell Orders: {len(sell_trades)}
- Total Amount Bought: ₹{total_bought:,.2f}
- Total Amount Sold: ₹{total_sold:,.2f}
- Net Cash Flow: ₹{total_sold - total_bought:,.2f}

RECENT TRADES:
"""
        
        for _, trade in trades_df.head(10).iterrows():
            report += f"- {trade['action']} {trade['symbol']} x{trade['quantity']} @ ₹{trade['price']:.2f} | {trade['reason'][:50]}...\n"
        
        conn.close()
        return report
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics"""
        conn = sqlite3.connect(self.db_manager.db_path)
        
        trades_df = pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp", conn)
        
        if trades_df.empty:
            return {}
        
        # Calculate win rate for completed trades (buy-sell pairs)
        symbols_traded = trades_df['symbol'].unique()
        completed_trades = []
        
        for symbol in symbols_traded:
            symbol_trades = trades_df[trades_df['symbol'] == symbol].sort_values('timestamp')
            
            buy_trades = symbol_trades[symbol_trades['action'] == 'BUY']
            sell_trades = symbol_trades[symbol_trades['action'] == 'SELL']
            
            # Match buy-sell pairs (simplified)
            for _, sell_trade in sell_trades.iterrows():
                matching_buys = buy_trades[buy_trades['timestamp'] < sell_trade['timestamp']]
                if not matching_buys.empty:
                    buy_trade = matching_buys.iloc[-1]  # Get most recent buy
                    pnl = (sell_trade['price'] - buy_trade['price']) * sell_trade['quantity']
                    completed_trades.append({
                        'symbol': symbol,
                        'buy_price': buy_trade['price'],
                        'sell_price': sell_trade['price'],
                        'quantity': sell_trade['quantity'],
                        'pnl': pnl,
                        'return_pct': (sell_trade['price'] - buy_trade['price']) / buy_trade['price'] * 100
                    })
        
        if not completed_trades:
            conn.close()
            return {'total_trades': len(trades_df), 'completed_trades': 0}
        
        completed_df = pd.DataFrame(completed_trades)
        winning_trades = completed_df[completed_df['pnl'] > 0]
        
        metrics = {
            'total_trades': len(trades_df),
            'completed_trades': len(completed_df),
            'winning_trades': len(winning_trades),
            'win_rate': len(winning_trades) / len(completed_df) * 100 if completed_df else 0,
            'total_pnl': completed_df['pnl'].sum(),
            'avg_return_per_trade': completed_df['return_pct'].mean(),
            'best_trade': completed_df['pnl'].max() if not completed_df.empty else 0,
            'worst_trade': completed_df['pnl'].min() if not completed_df.empty else 0,
            'total_volume': trades_df['amount'].sum()
        }
        
        conn.close()
        return metrics

def main():
    """Main function to run the trading system"""
    
    # Configuration
    GEMINI_API_KEY = "AIzaSyBD-5gGQTgEgh6MkmbZUnXxUIdU_1ELjZE"  # Replace with your actual API key
    
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        print("Please set your Gemini API key in the GEMINI_API_KEY variable")
        return
    
    # Initialize trading system
    trading_system = TradingSystem(GEMINI_API_KEY)
    reporter = TradingReporter(trading_system.db_manager)
    
    print("=== INDIAN STOCK TRADING SYSTEM STARTED ===")
    print(f"Initial Capital: ₹{trading_system.trading_engine.initial_capital:,.2f}")
    print(f"Tracking {len(NIFTY_50_SYMBOLS)} Nifty 50 stocks")
    print("=" * 50)
    
    try:
        # Run trading cycles
        cycle_count = 0
        while True:
            cycle_count += 1
            print(f"\n--- TRADING CYCLE {cycle_count} ---")
            
            # Run trading cycle
            trading_system.run_trading_cycle()
            
            # Generate reports
            portfolio_summary = trading_system.get_portfolio_summary()
            print(f"\nPortfolio Value: ₹{portfolio_summary['current_value']:,.2f}")
            print(f"Total Return: ₹{portfolio_summary['total_return']:,.2f} ({portfolio_summary['return_percentage']:.2f}%)")
            print(f"Active Positions: {portfolio_summary['active_positions']}")
            
            # Show recent trades
            recent_trades = trading_system.get_trade_history(5)
            if recent_trades:
                print("\nRecent Trades:")
                for trade in recent_trades:
                    print(f"- {trade['action']} {trade['symbol']} x{trade['quantity']} @ ₹{trade['price']:.2f}")
            
            # Performance metrics
            if cycle_count % 5 == 0:  # Every 5 cycles
                metrics = reporter.get_performance_metrics()
                if metrics:
                    print(f"\nPerformance Metrics (After {cycle_count} cycles):")
                    print(f"- Total Trades: {metrics['total_trades']}")
                    print(f"- Win Rate: {metrics['win_rate']:.1f}%")
                    print(f"- Total P&L: ₹{metrics['total_pnl']:,.2f}")
                    print(f"- Avg Return per Trade: {metrics['avg_return_per_trade']:.2f}%")
            
            # Wait before next cycle (in production, you might run this daily/hourly)
            print(f"\nWaiting 30 seconds before next cycle...")
            time.sleep(30)  # 5 minutes between cycles
            
    except KeyboardInterrupt:
        print("\n\nTrading system stopped by user")
        
        # Final report
        final_summary = trading_system.get_portfolio_summary()
        final_metrics = reporter.get_performance_metrics()
        
        print("\n=== FINAL SUMMARY ===")
        print(f"Initial Capital: ₹{trading_system.trading_engine.initial_capital:,.2f}")
        print(f"Final Portfolio Value: ₹{final_summary['current_value']:,.2f}")
        print(f"Total Return: ₹{final_summary['total_return']:,.2f} ({final_summary['return_percentage']:.2f}%)")
        print(f"Total Trades Executed: {final_metrics.get('total_trades', 0)}")
        print(f"Win Rate: {final_metrics.get('win_rate', 0):.1f}%")
        print("\nTrading system shut down gracefully.")

if __name__ == "__main__":
    main()

# Additional utility functions for analysis and monitoring

class RiskManager:
    """Risk management utilities"""
    
    def __init__(self, max_position_size: float = 0.05, max_daily_loss: float = 0.02):
        self.max_position_size = max_position_size  # 5% of portfolio
        self.max_daily_loss = max_daily_loss  # 2% daily loss limit
        self.daily_pnl = 0.0
        self.day_start_value = 0.0
    
    def check_position_size(self, position_value: float, portfolio_value: float) -> bool:
        """Check if position size is within limits"""
        position_pct = position_value / portfolio_value
        return position_pct <= self.max_position_size
    
    def check_daily_loss_limit(self, current_portfolio_value: float) -> bool:
        """Check if daily loss limit is breached"""
        if self.day_start_value == 0:
            self.day_start_value = current_portfolio_value
            return True
        
        daily_loss = (self.day_start_value - current_portfolio_value) / self.day_start_value
        return daily_loss <= self.max_daily_loss
    
    def reset_daily_tracking(self, portfolio_value: float):
        """Reset daily tracking for new day"""
        self.day_start_value = portfolio_value
        self.daily_pnl = 0.0

class BacktestEngine:
    """Backtesting engine for strategy validation"""
    
    def __init__(self, trading_system: TradingSystem):
        self.trading_system = trading_system
    
    def run_backtest(self, start_date: str, end_date: str, symbols: List[str] = None):
        """Run backtest for specified period"""
        if symbols is None:
            symbols = NIFTY_50_SYMBOLS[:10]  # Test with subset for speed
        
        print(f"Running backtest from {start_date} to {end_date}")
        print(f"Testing {len(symbols)} symbols")
        
        # This would be implemented to simulate historical trading
        # For now, it's a placeholder for the backtesting functionality
        pass

# Configuration and deployment helpers

def setup_environment():
    """Setup environment and dependencies"""
    required_packages = [
        'yfinance', 'pandas', 'numpy', 'requests', 'beautifulsoup4',
        'sqlite3', 'ta', 'textblob', 'google-generativeai'
    ]
    
    print("Required packages for the trading system:")
    for package in required_packages:
        print(f"- {package}")
    
    print("\nInstall with: pip install " + " ".join(required_packages))

def create_config_file():
    """Create configuration file template"""
    config_template = {
        "gemini_api_key": "AIzaSyBD-5gGQTgEgh6MkmbZUnXxUIdU_1ELjZE",
        "initial_capital": 1000000.0,
        "position_size_pct": 0.05,
        "max_positions": 10,
        "trading_frequency": "daily",
        "risk_management": {
            "max_daily_loss": 0.02,
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.10
        },
        "news_sources": [
            "moneycontrol.com",
            "economictimes.indiatimes.com"
        ]
    }
    
    with open("trading_config.json", "w") as f:
        json.dump(config_template, f, indent=4)
    
    print("Configuration file 'trading_config.json' created")
    print("Please update the API key and other settings as needed")

# Monitoring and alerting

class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self):
        self.alert_thresholds = {
            'daily_loss': 0.05,  # 5% daily loss
            'portfolio_drop': 0.10,  # 10% portfolio drop
            'consecutive_losses': 5
        }
    
    def check_alerts(self, portfolio_summary: Dict[str, Any], recent_trades: List[Dict[str, Any]]):
        """Check for alert conditions"""
        alerts = []
        
        # Check daily loss
        if portfolio_summary['return_percentage'] < -self.alert_thresholds['daily_loss'] * 100:
            alerts.append(f"Daily loss threshold breached: {portfolio_summary['return_percentage']:.2f}%")
        
        # Check consecutive losses
        if len(recent_trades) >= self.alert_thresholds['consecutive_losses']:
            recent_pnls = []
            for trade in recent_trades[:self.alert_thresholds['consecutive_losses']]:
                if 'PnL:' in trade.get('reason', ''):
                    try:
                        pnl_str = trade['reason'].split('PnL: ₹')[1].split()[0]
                        pnl = float(pnl_str)
                        recent_pnls.append(pnl)
                    except:
                        continue
            
            if len(recent_pnls) >= self.alert_thresholds['consecutive_losses']:
                if all(pnl < 0 for pnl in recent_pnls):
                    alerts.append(f"Consecutive losses detected: {len(recent_pnls)} losing trades")
        
        return alerts

# Usage example and documentation
"""
USAGE INSTRUCTIONS:

1. Install required packages:
   pip install yfinance pandas numpy requests beautifulsoup4 ta textblob google-generativeai

2. Get Gemini API key:
   - Go to Google AI Studio (https://makersuite.google.com/)
   - Create API key
   - Replace "YOUR_GEMINI_API_KEY_HERE" with your actual key

3. Run the system:
   python trading_system.py

4. Monitor the logs and database:
   - Trades are logged to console and saved in trading_system.db
   - Portfolio performance is tracked and reported
   - Memory system stores historical patterns

5. Customize parameters:
   - Adjust position sizing in PaperTradingEngine
   - Modify technical indicators in TechnicalAnalyzer
   - Update news sources in DataCollector
   - Fine-tune AI prompts in GeminiAnalyzer

FEATURES IMPLEMENTED:
✓ Historical data collection for Nifty 50 stocks
✓ Layered memory system (short-term and long-term)
✓ Technical analysis with multiple indicators
✓ News scraping from Indian financial sites
✓ AI-powered trading decisions with Gemini 2.0 Flash
✓ Paper trading with portfolio management
✓ Trade logging with detailed reasoning
✓ Performance tracking and reporting
✓ Risk management and position sizing
✓ Database storage for all operations

NEXT STEPS FOR ENHANCEMENT:
- Add more sophisticated memory retrieval with embeddings
- Implement advanced risk management rules
- Add more technical indicators and patterns
- Enhance news sentiment analysis
- Add backtesting capabilities
- Implement real-time alerts and notifications
- Add visualization dashboard
- Optimize AI prompts for better decision making
"""