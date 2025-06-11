from typing import Dict, Any
import pandas as pd
from pathlib import Path
from loguru import logger
from puppy.models.agent import TradingAgent
from puppy.utils.data_loader import DataLoader
from puppy.utils.portfolio import Portfolio
from puppy.services.news_service import NewsService
from puppy.utils.real_time_data import RealTimeDataManager
import time
import signal
import sys
import threading
import random
import yfinance as yf

class Simulation:
    """Trading simulation with news integration"""
    
    def __init__(
        self,
        config: Dict[str, Any],
        mode: str,
        checkpoint_path: str,
        result_path: str
    ):
        self.config = config
        self.mode = mode
        self.checkpoint_path = Path(checkpoint_path)
        self.result_path = Path(result_path)
        self.running = True
        self.simulation_thread = None
        
        # Initialize components
        self.data_loader = DataLoader(config["market"])
        self.portfolio = Portfolio(
            initial_capital=1000000,  # Set to 1 million
            position_size_limit=200000  # 20% of initial capital
        )
        self.agent = TradingAgent(
            config=config["agent"],
            chat_config=config["chat"],
            memory_config=config["memory"]
        )
        
        # Initialize services
        self.news_service = NewsService()
        self.real_time_data = RealTimeDataManager()
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info(f"Initialized simulation in {mode} mode")
        
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        logger.info("\nReceived stop signal. Finishing current iteration...")
        self.running = False
        
    def run(self):
        """Run the trading simulation"""
        try:
            initial_capital = self.portfolio.initial_capital
            iteration = 0
            logger.info(f"Starting with initial capital: ₹{initial_capital:,.2f}")

            if self.mode == "backtest":
                # Load all market data
                market_data = self.data_loader.load_data()
                all_dates = sorted(set(market_data.index.get_level_values("Date")))
                watched_symbols = self.config["market"]["symbols"]
                for current_date in all_dates:
                    iteration += 1
                    logger.info(f"\nBacktest Iteration {iteration} - {current_date.date()}")
                    # Get daily data for all symbols for this date
                    try:
                        daily_data = market_data.loc[current_date]
                    except Exception as e:
                        logger.error(f"No data for {current_date}: {e}")
                        continue
                    # Convert to MultiIndex for compatibility
                    daily_data.index = pd.MultiIndex.from_tuples(
                        [(current_date, idx) for idx in daily_data.index.get_level_values("Symbol")],
                        names=["Date", "Symbol"]
                    )
                    # Prepare daily_dict for agent memory
                    daily_dict = {"date": current_date, "data": []}
                    for symbol in watched_symbols:
                        try:
                            row = daily_data.loc[pd.IndexSlice[current_date, symbol], :]
                            current_price = float(row["Close"])
                            open_price = float(row["Open"])
                            high = float(row["High"])
                            low = float(row["Low"])
                            prev_close = float(row["Close"])
                            volume = float(row["Volume"])
                            daily_return = (current_price - prev_close) / prev_close if prev_close else 0
                            rsi = float(row["RSI"]) if pd.notna(row["RSI"]) else 50.0
                            ma_20 = float(row["20d_MA"]) if pd.notna(row["20d_MA"]) else None
                            ma_50 = float(row["50d_MA"]) if pd.notna(row["50d_MA"]) else None
                            volume_ma = float(row["Volume_MA"]) if pd.notna(row["Volume_MA"]) else None
                            daily_dict["data"].append({
                                "Symbol": symbol,
                                "Open": open_price,
                                "High": high,
                                "Low": low,
                                "Close": current_price,
                                "Volume": volume,
                                "Daily_Return": daily_return,
                                "RSI": rsi,
                                "20d_MA": ma_20,
                                "50d_MA": ma_50,
                                "Volume_MA": volume_ma
                            })
                        except Exception as e:
                            logger.error(f"Error processing symbol {symbol} on {current_date}: {e}")
                            continue
                    # Update agent's memory
                    self.agent.update_memory(daily_dict)
                    
                    # Get trading decisions from agent
                    decisions = self.agent.make_decisions(
                        daily_data,
                        self.portfolio.get_state(),
                        current_date
                    )
                    
                    # Log decisions
                    if decisions:
                        logger.info(f"\nTrading Decisions for {current_date}:")
                        for symbol, action in decisions.items():
                            logger.info(f"{symbol}: {action['action'].upper()} {action['quantity']} shares at ₹{action['price']:.2f}")
                            logger.info(f"Reason: {action.get('reason', 'No reason provided')}")
                    
                    # Execute trades
                    for symbol, action in decisions.items():
                        try:
                            if action["action"] == "buy":
                                success = self.portfolio.buy(
                                    symbol,
                                    action["quantity"],
                                    action["price"],
                                    action.get("reason", "")
                                )
                                if success:
                                    logger.info(f"Successfully bought {action['quantity']} shares of {symbol} at ₹{action['price']:.2f}")
                                else:
                                    logger.warning(f"Failed to buy {symbol}")
                                    
                            elif action["action"] == "sell":
                                success = self.portfolio.sell(
                                    symbol,
                                    action["quantity"],
                                    action["price"],
                                    action.get("reason", "")
                                )
                                if success:
                                    logger.info(f"Successfully sold {action['quantity']} shares of {symbol} at ₹{action['price']:.2f}")
                                else:
                                    logger.warning(f"Failed to sell {symbol}")
                        except Exception as e:
                            logger.error(f"Error executing trade for {symbol}: {str(e)}")
                    
                    # Save daily results
                    self._save_daily_results(current_date)
                    
                    # Print iteration summary
                    current_value = self.portfolio.get_total_value()
                    profit_loss = current_value - initial_capital
                    profit_loss_pct = (profit_loss / initial_capital) * 100
                    
                    logger.info("\nIteration Summary:")
                    logger.info(f"Initial Capital: ₹{initial_capital:,.2f}")
                    logger.info(f"Current Value:  ₹{current_value:,.2f}")
                    logger.info(f"Profit/Loss:    ₹{profit_loss:,.2f} ({profit_loss_pct:,.2f}%)")
                # Print final summary when stopped
                final_value = self.portfolio.get_total_value()
                total_profit_loss = final_value - initial_capital
                total_profit_loss_pct = (total_profit_loss / initial_capital) * 100
                logger.info("\nFinal Summary:")
                logger.info(f"Initial Capital: ₹{initial_capital:,.2f}")
                logger.info(f"Final Value:    ₹{final_value:,.2f}")
                logger.info(f"Total P/L:      ₹{total_profit_loss:,.2f} ({total_profit_loss_pct:,.2f}%)")
                self._save_final_results()
                logger.info("Backtest completed")
                return
            
            while self.running:
                iteration += 1
                logger.info(f"\nIteration {iteration}")
                
                # Check if market is open
                if not self.real_time_data.is_market_open():
                    logger.info("Market is closed. Waiting for next iteration...")
                    time.sleep(60)  # Wait 1 minute before checking again
                    continue
                
                # Fetch latest market news
                market_news = self.news_service.get_latest_market_news(pages=2)
                logger.info(f"Fetched {len(market_news)} market news articles")
                for article in market_news:
                    logger.info(f"NEWS: {article.get('title', str(article))}")
                
                # Get watched symbols from config (now all 50)
                watched_symbols = self.config["market"]["symbols"]
                # Fetch real-time prices for all symbols
                real_time_prices = self.get_realtime_prices(watched_symbols)
                # Initialize daily_dict for this iteration
                from datetime import datetime
                daily_dict = {"date": datetime.now(), "data": []}
                # Optionally, create a dummy daily_data DataFrame for compatibility
                daily_data_rows = []
                for symbol in watched_symbols:
                    price = real_time_prices.get(symbol)
                    if price is None:
                        continue
                    # For test mode, we may not have all other fields, so fill with price or None
                    row = {
                        "Open": price,
                        "High": price,
                        "Low": price,
                        "Close": price,
                        "Volume": 0,
                        "RSI": 50.0,
                        "20d_MA": None,
                        "50d_MA": None,
                        "Volume_MA": None
                    }
                    daily_data_rows.append((symbol, row))
                    daily_dict["data"].append({
                        "Symbol": symbol,
                        "Open": price,
                        "High": price,
                        "Low": price,
                        "Close": price,
                        "Volume": 0,
                        "Daily_Return": 0,
                        "RSI": 50.0,
                        "20d_MA": None,
                        "50d_MA": None,
                        "Volume_MA": None
                    })
                # Create a DataFrame for daily_data for compatibility
                if daily_data_rows:
                    daily_data = pd.DataFrame([row for _, row in daily_data_rows],
                                             index=pd.MultiIndex.from_tuples([(datetime.now(), symbol) for symbol, _ in daily_data_rows], names=["Date", "Symbol"]))
                else:
                    daily_data = pd.DataFrame()
                # Update agent's memory with new market data if there is any data
                if daily_dict["data"]:
                    self.agent.update_memory(daily_dict)
                if self.mode == "train":
                    # In training mode, just update memory
                    continue
                # Get trading decisions from agent
                decisions = self.agent.make_decisions(
                    daily_data,
                    self.portfolio.get_state(),
                    datetime.now()
                )
                
                # Log decisions
                if decisions:
                    logger.info(f"\nTrading Decisions for {datetime.now()}:")
                    for symbol, action in decisions.items():
                        logger.info(f"{symbol}: {action['action'].upper()} {action['quantity']} shares at ₹{action['price']:.2f}")
                        logger.info(f"Reason: {action.get('reason', 'No reason provided')}")
                else:
                    logger.info("No trading decisions for this iteration")
                
                # Execute trades
                for symbol, action in decisions.items():
                    try:
                        if action["action"] == "buy":
                            success = self.portfolio.buy(
                                symbol,
                                action["quantity"],
                                action["price"],
                                action.get("reason", "")
                            )
                            if success:
                                logger.info(f"Successfully bought {action['quantity']} shares of {symbol} at ₹{action['price']:.2f}")
                            else:
                                logger.warning(f"Failed to buy {symbol}")
                                
                        elif action["action"] == "sell":
                            success = self.portfolio.sell(
                                symbol,
                                action["quantity"],
                                action["price"],
                                action.get("reason", "")
                            )
                            if success:
                                logger.info(f"Successfully sold {action['quantity']} shares of {symbol} at ₹{action['price']:.2f}")
                            else:
                                logger.warning(f"Failed to sell {symbol}")
                    except Exception as e:
                        logger.error(f"Error executing trade for {symbol}: {str(e)}")
                
                # Save daily results
                self._save_daily_results(datetime.now())
                # Print iteration summary
                current_value = self.portfolio.get_total_value()
                profit_loss = current_value - initial_capital
                profit_loss_pct = (profit_loss / initial_capital) * 100
                logger.info("\nIteration Summary:")
                logger.info(f"Initial Capital: ₹{initial_capital:,.2f}")
                logger.info(f"Current Value:  ₹{current_value:,.2f}")
                logger.info(f"Profit/Loss:    ₹{profit_loss:,.2f} ({profit_loss_pct:,.2f}%)")
                # Sleep before next iteration (reduced from 5 minutes to 1 minute)
                time.sleep(60)
                
            # Print final summary when stopped
            final_value = self.portfolio.get_total_value()
            total_profit_loss = final_value - initial_capital
            total_profit_loss_pct = (total_profit_loss / initial_capital) * 100
            
            logger.info("\nFinal Summary:")
            logger.info(f"Initial Capital: ₹{initial_capital:,.2f}")
            logger.info(f"Final Value:    ₹{final_value:,.2f}")
            logger.info(f"Total P/L:      ₹{total_profit_loss:,.2f} ({total_profit_loss_pct:,.2f}%)")
            
            self._save_final_results()
            logger.info("Simulation completed")
        except Exception as e:
            logger.error(f"Error in simulation: {str(e)}")
            raise
    
    def _save_daily_results(self, date):
        """Save daily portfolio state and performance metrics"""
        results = {
            "date": date,
            "portfolio_value": self.portfolio.get_total_value(),
            "cash": self.portfolio.cash,
            "positions": self.portfolio.positions
        }
        # Save to file
        
    def _save_final_results(self):
        """Save final simulation results and performance metrics"""
        # Calculate and save final metrics
        pass 

    def start_non_blocking(self):
        """Start simulation in a separate thread"""
        if self.simulation_thread is None or not self.simulation_thread.is_alive():
            self.running = True
            self.simulation_thread = threading.Thread(target=self.run)
            self.simulation_thread.daemon = True
            self.simulation_thread.start()
            logger.info("Started simulation in non-blocking mode")
    
    def stop(self):
        """Stop the simulation"""
        self.running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=5)
            logger.info("Stopped simulation")

    def get_realtime_prices(self, symbols):
        tickers = [f"{sym}.NS" for sym in symbols]
        data = yf.download(tickers, period="1d", interval="1m")
        last_prices = {}
        for sym in symbols:
            try:
                last_prices[sym] = float(data['Close'][f"{sym}.NS"].dropna()[-1])
            except Exception:
                last_prices[sym] = None
        return last_prices 