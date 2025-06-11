from typing import Dict, Any, List
import pandas as pd
from datetime import datetime
from loguru import logger

class LayeredMemory:
    """Layered memory system for storing and retrieving market data and events"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.short_term = []  # Recent memories
        self.long_term = []   # Important memories
        self.max_short_term = config["memory"]["short_term_capacity"]
        self.max_long_term = config["memory"]["long_term_capacity"]
        self.relevance_threshold = config["memory"]["relevance_threshold"]
        
    def add_memory(self, data: Dict[str, Any], memory_type: str):
        """Add new memory entry"""
        try:
            entry = self._create_memory_entry(data, memory_type)
            
            # Add to short-term memory
            self.short_term.append(entry)
            
            # Check if it should be added to long-term memory
            if entry["importance_score"] >= self.relevance_threshold:
                self.long_term.append(entry)
                
            # Maintain memory size limits
            self._maintain_memory_size()
            
        except Exception as e:
            logger.error(f"Error adding memory: {str(e)}")
            
    def _create_memory_entry(self, data: Dict[str, Any], memory_type: str) -> Dict[str, Any]:
        """Create a memory entry with metadata"""
        return {
            "timestamp": datetime.now(),
            "type": memory_type,
            "data": data,
            "importance_score": self._calculate_importance(data)
        }
        
    def _calculate_importance(self, data: Dict[str, Any]) -> float:
        """Calculate importance score for memory entry"""
        importance = 0.0
        
        # Check for market data
        if "data" in data:
            for stock_data in data["data"]:
                # Volume spike
                volume = stock_data.get("Volume", 0)
                volume_ma = stock_data.get("Volume_MA")
                if volume_ma is not None and volume > volume_ma * 1.5:
                    importance += 0.3
                    
                # Price movement
                daily_return = stock_data.get("Daily_Return", 0)
                if abs(daily_return) > 0.05:  # 5% move
                    importance += 0.2
                    
                # Technical indicators
                rsi = stock_data.get("RSI", 50)
                if rsi < 30 or rsi > 70:  # Extreme RSI
                    importance += 0.2
                    
                # Moving average crossovers
                ma_20 = stock_data.get("20d_MA")
                ma_50 = stock_data.get("50d_MA")
                if ma_20 is not None and ma_50 is not None:
                    if ma_20 > ma_50:  # Bullish crossover
                        importance += 0.3
                    elif ma_20 < ma_50:  # Bearish crossover
                        importance += 0.3
                        
        return min(importance, 1.0)  # Cap at 1.0
        
    def _maintain_memory_size(self):
        """Maintain memory size limits"""
        # Sort by importance and timestamp
        self.short_term.sort(key=lambda x: (x["importance_score"], x["timestamp"]), reverse=True)
        self.long_term.sort(key=lambda x: (x["importance_score"], x["timestamp"]), reverse=True)
        
        # Trim to size limits
        if len(self.short_term) > self.max_short_term:
            self.short_term = self.short_term[:self.max_short_term]
        if len(self.long_term) > self.max_long_term:
            self.long_term = self.long_term[:self.max_long_term]
            
    def retrieve_relevant_memories(self, query: str) -> List[Dict[str, Any]]:
        """Retrieve memories relevant to the query"""
        # For now, just return recent important memories
        relevant_memories = []
        
        # Add recent important memories from short-term
        for memory in self.short_term:
            if memory["importance_score"] >= self.relevance_threshold:
                relevant_memories.append(memory)
                
        # Add important memories from long-term
        for memory in self.long_term:
            if memory["importance_score"] >= self.relevance_threshold:
                relevant_memories.append(memory)
                
        return relevant_memories 