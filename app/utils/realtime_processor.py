import threading
import queue
import time
from datetime import datetime
from typing import Dict, Any, List
import json
from pathlib import Path
import subprocess
import os

class RealtimeProcessor:
    def __init__(self):
        self.data_queue = queue.Queue()
        self.running = False
        self.finmem_process = None
        self.data_thread = None
        self.last_update = None
        self.current_data = {
            "portfolio": {},
            "transactions": [],
            "capital": 0,
            "initial_capital": 0,
            "news": []
        }
    
    def start_finmem(self, config: Dict[str, Any] = None):
        """Start the FinMem India process"""
        if self.running:
            return
        
        self.running = True
        
        # Create a data directory if it doesn't exist
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        # Save configuration if provided
        if config:
            config_path = data_dir / "config.json"
            with open(config_path, "w") as f:
                json.dump(config, f)
        
        # Start FinMem India process
        try:
            # Start the main FinMem process
            self.finmem_process = subprocess.Popen(
                ["python", "finmem_india/main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Start data processing thread
            self.data_thread = threading.Thread(target=self._process_data)
            self.data_thread.daemon = True
            self.data_thread.start()
            
        except Exception as e:
            self.running = False
            raise Exception(f"Failed to start FinMem India: {str(e)}")
    
    def stop_finmem(self):
        """Stop the FinMem India process"""
        self.running = False
        
        if self.finmem_process:
            self.finmem_process.terminate()
            self.finmem_process = None
        
        if self.data_thread:
            self.data_thread.join(timeout=1)
            self.data_thread = None
    
    def _process_data(self):
        """Process data from FinMem India"""
        while self.running:
            try:
                # Read output from FinMem process
                if self.finmem_process:
                    line = self.finmem_process.stdout.readline()
                    if line:
                        # Parse and process the data
                        self._update_data(line.strip())
                
                # Update timestamp
                self.last_update = datetime.now()
                
                # Small delay to prevent CPU overuse
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error processing data: {str(e)}")
                time.sleep(1)
    
    def _update_data(self, data_line: str):
        """Update current data with new information"""
        try:
            data = json.loads(data_line)
            
            # Update relevant sections based on data type
            if "type" in data:
                if data["type"] == "portfolio_update":
                    self.current_data["portfolio"] = data["portfolio"]
                    self.current_data["capital"] = data["capital"]
                
                elif data["type"] == "transaction":
                    self.current_data["transactions"].append(data["transaction"])
                
                elif data["type"] == "news":
                    self.current_data["news"].insert(0, data["news"])
                    # Keep only latest 100 news items
                    self.current_data["news"] = self.current_data["news"][:100]
            
            # Put updated data in queue for UI
            self.data_queue.put(self.current_data.copy())
            
        except json.JSONDecodeError:
            print(f"Invalid JSON data: {data_line}")
        except Exception as e:
            print(f"Error updating data: {str(e)}")
    
    def get_latest_data(self) -> Dict[str, Any]:
        """Get the latest data for UI updates"""
        return self.current_data.copy()
    
    def is_running(self) -> bool:
        """Check if FinMem India is running"""
        return self.running and self.finmem_process is not None
    
    def get_last_update(self) -> datetime:
        """Get the timestamp of the last update"""
        return self.last_update 