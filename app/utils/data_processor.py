from typing import Dict, Any, Optional, List
from datetime import datetime
import threading
import queue
import time
import subprocess
from pathlib import Path
import json
from .trading import TradingSimulator
from .market_hours import MarketHours
from .news_scraper import NewsAggregator
from .test_data import get_nifty50_symbols
from .finmem_integration import FinMemManager

class DataProcessor:
    def __init__(self):
        self.mode = None  # 'test' or 'real'
        self.simulator = None
        self.finmem = None
        self.running = False
        self.data_thread = None
        self.data_queue = queue.Queue()
        self.last_update = None
        self.market_hours = MarketHours()
        self.news_aggregator = None
        self.current_state = {
            'user': None,
            'capital': 0,
            'initial_capital': 0,
            'total_value': 0,
            'total_pl': 0,
            'pl_pct': 0,
            'portfolio': {},
            'transactions': [],
            'risk_profile': None,
            'last_update': None,
            'news': [],
            'logs': [],
            'market_status': None
        }
        self.max_logs = 1000  # Maximum number of log entries to keep
    
    def start(self, mode: str, config: Dict[str, Any]):
        """Start data processing in specified mode"""
        if self.running:
            return
        
        self.mode = mode
        self.running = True
        
        # Initialize news aggregator
        symbols = get_nifty50_symbols()
        self.news_aggregator = NewsAggregator(symbols)
        self.news_aggregator.start()
        self._add_log("Started news aggregation")
        
        # Load previous state for real-time mode
        if mode == 'real':
            self._load_state()
            
            # Update config with previous capital if not resetting
            if not config.get('reset_capital', False):
                saved_capital = self.current_state.get('capital')
                if saved_capital is not None:
                    config['initial_capital'] = saved_capital
                    self._add_log(f"Restored previous capital: {saved_capital}")
            
            # Initialize FinMem
            try:
                self.finmem = FinMemManager()
                self.finmem.initialize(config)
                self._add_log("Initialized FinMem trading")
                
                # Start data processing thread
                self.data_thread = threading.Thread(target=self._run_real_updates)
                self.data_thread.daemon = True
                self.data_thread.start()
                
            except Exception as e:
                self.running = False
                error_msg = f"Failed to initialize FinMem: {str(e)}"
                self._add_log(error_msg, level="ERROR")
                raise Exception(error_msg)
        
        elif mode == 'test':
            # Initialize test simulator
            self.simulator = TradingSimulator(config)
            
            # Start update thread
            self.data_thread = threading.Thread(target=self._run_test_updates)
            self.data_thread.daemon = True
            self.data_thread.start()
            
            # Log startup
            self._add_log("Started test mode simulation")
        
        else:  # real-time mode
            # Save configuration
            config_path = Path("config/finmem_config.json")
            config_path.parent.mkdir(exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(config, f)
            
            # Start FinMem India process
            try:
                self._add_log("Starting FinMem India process...")
                self.finmem_process = subprocess.Popen(
                    ["python", "finmem_india/main.py", "--config", str(config_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    bufsize=1  # Line buffered
                )
                
                # Start data processing thread
                self.data_thread = threading.Thread(target=self._run_real_updates)
                self.data_thread.daemon = True
                self.data_thread.start()
                
                # Start error stream reader thread
                self.error_thread = threading.Thread(target=self._monitor_errors)
                self.error_thread.daemon = True
                self.error_thread.start()
                
                self._add_log("FinMem India process started successfully")
                
            except Exception as e:
                self.running = False
                error_msg = f"Failed to start FinMem India: {str(e)}"
                self._add_log(error_msg, level="ERROR")
                raise Exception(error_msg)
    
    def stop(self):
        """Stop data processing"""
        if not self.running:
            return
        
        self._add_log("Stopping data processing...")
        self.running = False
        
        if self.finmem_process:
            self._add_log("Terminating FinMem India process...")
            self.finmem_process.terminate()
            self.finmem_process = None
        
        if self.data_thread:
            self.data_thread.join(timeout=1)
            self.data_thread = None
        
        if hasattr(self, 'error_thread'):
            self.error_thread.join(timeout=1)
        
        if self.news_aggregator:
            self.news_aggregator.stop()
            self._add_log("Stopped news aggregation")
        
        self.simulator = None
        self.mode = None
        self.last_update = None
        self._add_log("Data processing stopped")
    
    def _add_log(self, message: str, level: str = "INFO"):
        """Add a log entry with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message
        }
        
        self.current_state['logs'].append(log_entry)
        
        # Keep only the last max_logs entries
        if len(self.current_state['logs']) > self.max_logs:
            self.current_state['logs'] = self.current_state['logs'][-self.max_logs:]
        
        # Update UI
        self.data_queue.put(self.current_state.copy())
    
    def _monitor_errors(self):
        """Monitor the error stream from FinMem process"""
        while self.running and self.finmem_process:
            try:
                error_line = self.finmem_process.stderr.readline()
                if error_line:
                    self._add_log(error_line.strip(), level="ERROR")
            except Exception as e:
                print(f"Error monitoring stderr: {str(e)}")
                time.sleep(1)
    
    def _update_market_status(self):
        """Update market status"""
        self.current_state['market_status'] = self.market_hours.get_market_status()
        
        # Log market status changes
        status = self.current_state['market_status']['status']
        message = self.current_state['market_status']['message']
        self._add_log(f"Market Status: {status} - {message}")
    
    def _run_test_updates(self):
        """Run test simulation updates"""
        while self.running:
            try:
                # Update market status
                self._update_market_status()
                
                # Only update simulation during market hours
                if self.market_hours.is_market_open():
                    # Update simulator
                    self.simulator.update()
                    
                    # Get current state
                    state = self.simulator.get_state()
                    
                    # Update current state
                    self.current_state.update({
                        'user': state['user'],
                        'capital': state['capital'],
                        'initial_capital': state['initial_capital'],
                        'total_value': state['total_value'],
                        'total_pl': state['total_pl'],
                        'pl_pct': state['pl_pct'],
                        'portfolio': state['portfolio'],
                        'transactions': state['transactions'],
                        'risk_profile': state['risk_profile']
                    })
                    
                    self.last_update = datetime.now()
                    
                    # Update news
                    if self.news_aggregator:
                        self.current_state['news'] = self.news_aggregator.get_latest_news()
                    
                    # Put state in queue for UI
                    self.data_queue.put(self.current_state.copy())
                
                # Small delay between updates
                time.sleep(0.1)
                
            except Exception as e:
                error_msg = f"Error in test updates: {str(e)}"
                self._add_log(error_msg, level="ERROR")
                time.sleep(1)
    
    def _run_real_updates(self):
        """Process real-time updates from FinMem"""
        while self.running:
            try:
                # Update market status
                self._update_market_status()
                
                if self.finmem:
                    # Get latest state from FinMem
                    state = self.finmem.update()
                    
                    # Update current state
                    self.current_state.update(state)
                    self.last_update = datetime.now()
                    
                    # Update news
                    if self.news_aggregator:
                        self.current_state['news'] = self.news_aggregator.get_latest_news()
                    
                    # Put updated state in queue for UI
                    self.data_queue.put(self.current_state.copy())
                
                time.sleep(1)  # Update every second
                
            except Exception as e:
                error_msg = f"Error in real-time updates: {str(e)}"
                self._add_log(error_msg, level="ERROR")
                time.sleep(1)
    
    def _save_state(self):
        """Save current state to file"""
        if self.mode == 'real':  # Only save state in real-time mode
            state_file = Path("data/finmem_state.json")
            state_file.parent.mkdir(exist_ok=True)
            
            # Save relevant state data
            save_data = {
                'capital': self.current_state['capital'],
                'initial_capital': self.current_state['initial_capital'],
                'portfolio': self.current_state['portfolio'],
                'transactions': self.current_state['transactions'],
                'risk_profile': self.current_state['risk_profile'],
                'user': self.current_state['user'],
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(state_file, "w") as f:
                json.dump(save_data, f, indent=2)
    
    def _load_state(self):
        """Load previous state from file"""
        state_file = Path("data/finmem_state.json")
        if state_file.exists():
            try:
                with open(state_file, "r") as f:
                    saved_state = json.load(f)
                
                # Update current state with saved data
                self.current_state.update(saved_state)
                self._add_log("Loaded previous trading state")
            except Exception as e:
                self._add_log(f"Error loading previous state: {str(e)}", level="ERROR")
    
    def reset_capital(self, new_capital: float):
        """Reset capital to new value"""
        if self.mode == 'real':
            if self.finmem:
                success = self.finmem.reset_capital(new_capital)
                if success:
                    self._add_log(f"Reset capital to {new_capital}")
                else:
                    self._add_log("Failed to reset capital", level="ERROR")
        else:  # test mode
            if self.simulator:
                self.simulator.reset_capital(new_capital)
                self._add_log(f"Reset capital to {new_capital}")
    
    def _process_real_data(self, data_line: str):
        """Process real-time data updates"""
        try:
            data = json.loads(data_line)
            
            # Update state based on data type
            if data.get("type") == "state_update":
                self.current_state.update(data["state"])
                self.last_update = datetime.now()
                
                # Save state after each update
                self._save_state()
            
            # Put updated state in queue for UI
            self.data_queue.put(self.current_state.copy())
            
        except json.JSONDecodeError:
            self._add_log(f"Invalid JSON data: {data_line}", level="ERROR")
        except Exception as e:
            self._add_log(f"Error processing data: {str(e)}", level="ERROR")
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current state data"""
        return self.current_state.copy()
    
    def is_running(self) -> bool:
        """Check if data processing is running"""
        return self.running
    
    def get_last_update(self) -> Optional[datetime]:
        """Get timestamp of last update"""
        return self.last_update
    
    def get_market_status(self) -> Dict[str, Any]:
        """Get current market status"""
        return self.current_state['market_status']
    
    def get_news(self) -> List[Dict[str, Any]]:
        """Get current news items"""
        return self.current_state['news']
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """Get current logs"""
        return self.current_state['logs'] 