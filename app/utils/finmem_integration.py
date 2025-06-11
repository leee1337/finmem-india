import requests
import json
from typing import Dict, Any, Optional
from datetime import datetime
import os
from pathlib import Path
import toml
from puppy.core.simulation import Simulation
from puppy.utils.config import load_config

class FinMemAPI:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('FINMEM_API_KEY')
        if not self.api_key:
            raise ValueError("FinMem API key not provided")
        
        self.base_url = "https://api.finmem.in/v1"  # Update with actual API endpoint
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
    
    def initialize_account(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize or get trading account details"""
        endpoint = f"{self.base_url}/account/initialize"
        response = self.session.post(endpoint, json=config)
        response.raise_for_status()
        return response.json()
    
    def get_account_status(self) -> Dict[str, Any]:
        """Get current account status"""
        endpoint = f"{self.base_url}/account/status"
        response = self.session.get(endpoint)
        response.raise_for_status()
        return response.json()
    
    def place_order(self, order_details: Dict[str, Any]) -> Dict[str, Any]:
        """Place a new order"""
        endpoint = f"{self.base_url}/orders"
        response = self.session.post(endpoint, json=order_details)
        response.raise_for_status()
        return response.json()
    
    def get_positions(self) -> Dict[str, Any]:
        """Get current positions"""
        endpoint = f"{self.base_url}/positions"
        response = self.session.get(endpoint)
        response.raise_for_status()
        return response.json()
    
    def get_orders(self) -> Dict[str, Any]:
        """Get order history"""
        endpoint = f"{self.base_url}/orders"
        response = self.session.get(endpoint)
        response.raise_for_status()
        return response.json()
    
    def get_market_data(self, symbols: list) -> Dict[str, Any]:
        """Get real-time market data for symbols"""
        endpoint = f"{self.base_url}/market/data"
        response = self.session.post(endpoint, json={'symbols': symbols})
        response.raise_for_status()
        return response.json()

class FinMemManager:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/config.toml"
        self.config = self._load_config()
        self.simulation = None
        self.last_update = None
        self.current_state = {
            'user': None,
            'capital': 0,
            'initial_capital': 0,
            'total_value': 0,
            'total_pl': 0,
            'pl_pct': 0,
            'portfolio': {},
            'transactions': [],
            'risk_profile': None
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load FinMem configuration"""
        try:
            if os.path.exists(self.config_path):
                return load_config(self.config_path)
            else:
                # Return default config if file doesn't exist
                return {
                    "market": {
                        "data_path": "data/market",
                        "symbols": []
                    },
                    "trading": {
                        "initial_capital": 100000,
                        "position_size_limit": 0.2
                    },
                    "agent": {
                        "model": "gpt-4",
                        "risk_profile": "moderate"
                    },
                    "chat": {
                        "system_prompt": "You are an expert Indian stock market trader.",
                        "max_tokens": 500
                    },
                    "memory": {
                        "max_days": 30
                    }
                }
        except Exception as e:
            print(f"Error loading config: {str(e)}")
            # Return default config on error
            return {
                "market": {
                    "data_path": "data/market",
                    "symbols": []
                },
                "trading": {
                    "initial_capital": 100000,
                    "position_size_limit": 0.2
                },
                "agent": {
                    "model": "gpt-4",
                    "risk_profile": "moderate"
                },
                "chat": {
                    "system_prompt": "You are an expert Indian stock market trader.",
                    "max_tokens": 500
                },
                "memory": {
                    "max_days": 30
                }
            }
    
    def _save_config(self):
        """Save current configuration"""
        try:
            Path(self.config_path).parent.mkdir(exist_ok=True)
            config_dict = {
                "market": {
                    "data_path": "data/market",
                    "symbols": self.config.get("watched_symbols", [])
                },
                "trading": {
                    "initial_capital": self.current_state["initial_capital"],
                    "position_size_limit": 0.2  # 20% of capital per position
                },
                "agent": {
                    "model": "gpt-4",
                    "risk_profile": self.current_state["risk_profile"]
                },
                "chat": {
                    "system_prompt": "You are an expert Indian stock market trader.",
                    "max_tokens": 500
                },
                "memory": {
                    "max_days": 30
                }
            }
            
            with open(self.config_path, "w") as f:
                toml.dump(config_dict, f)
        except Exception as e:
            print(f"Error saving config: {str(e)}")
    
    def initialize(self, config: Dict[str, Any]):
        """Initialize FinMem trading"""
        try:
            # Update state with config
            self.current_state.update({
                'user': config['user'],
                'initial_capital': float(config['initial_capital']),
                'capital': float(config['initial_capital']),
                'risk_profile': config['risk_profile']
            })
            
            # Save config
            self._save_config()
            
            # Initialize simulation
            self.simulation = Simulation(
                config=self._load_config(),
                mode="test" if config.get("mode") == "test" else "train",
                checkpoint_path="data/checkpoints",
                result_path="data/results"
            )
            
            # Start simulation in non-blocking mode
            self.simulation.start_non_blocking()
        except Exception as e:
            print(f"Error initializing FinMem: {str(e)}")
            raise
    
    def update(self) -> Dict[str, Any]:
        """Update current state with latest data"""
        try:
            if self.simulation:
                # Get portfolio state
                portfolio_state = self.simulation.portfolio.get_state()
                
                # Update state
                self.current_state.update({
                    'capital': portfolio_state['available_capital'],
                    'total_value': portfolio_state['total_value'],
                    'total_pl': portfolio_state['total_pl'],
                    'pl_pct': portfolio_state['pl_percentage'],
                    'portfolio': portfolio_state['positions'],
                    'transactions': portfolio_state['transactions']
                })
                
                self.last_update = datetime.now()
            
            return self.current_state
            
        except Exception as e:
            print(f"Error updating FinMem state: {str(e)}")
            return self.current_state
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state"""
        return self.current_state.copy()
    
    def reset_capital(self, new_capital: float):
        """Reset account with new capital"""
        try:
            # Update state
            self.current_state['initial_capital'] = new_capital
            self.current_state['capital'] = new_capital
            
            # Save config
            self._save_config()
            
            # Reinitialize simulation
            if self.simulation:
                self.simulation.portfolio.reset(new_capital)
            
            return True
        except Exception as e:
            print(f"Error resetting capital: {str(e)}")
            return False
    
    def stop(self):
        """Stop the simulation"""
        if self.simulation:
            self.simulation.running = False 