import google.generativeai as genai
from typing import Dict, Any, List
from loguru import logger
import json

class GeminiTrader:
    """Trading decision maker using Gemini 2.0 Flash"""
    
    def __init__(self, api_key: str, config: Dict[str, Any]):
        self.config = config
        genai.configure(api_key=api_key)
        
        # Initialize Gemini model
        generation_config = {
            "temperature": config["chat"]["temperature"],
            "top_p": config["chat"]["top_p"],
            "top_k": config["chat"]["top_k"],
            "max_output_tokens": config["chat"]["max_tokens"]
        }
        
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }
        ]
        
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        # Initialize chat
        self.chat = self.model.start_chat(history=[])
        self._initialize_context()
        
    def _initialize_context(self):
        """Initialize the chat with trading context"""
        system_prompt = f"""You are an expert Indian stock market trader with deep knowledge of Nifty 50 stocks.
Your personality traits:
- {self.config['agent']['personality']}
- Risk tolerance: {self.config['agent']['risk_tolerance']}
- Investment style: {self.config['agent']['investment_style']}
- Time horizon: {self.config['agent']['time_horizon']}

Your task is to analyze market data, news, and historical patterns to make trading decisions.
You should consider:
1. Technical indicators (RSI, Moving Averages, Volume)
2. Market conditions and trends
3. Historical patterns from memory
4. News sentiment and impact
5. Risk management rules:
   - Maximum position size: 20% of portfolio
   - Stop loss: 5%
   - Take profit: 15%
   - Minimum 100 shares per trade
   - Maximum 1000 shares per position

Always explain your reasoning and highlight key factors in your decisions."""
        
        self.chat.send_message(system_prompt)
        
    def make_decision(
        self,
        market_data: Dict[str, Any],
        portfolio_state: Dict[str, Any],
        memories: List[Dict[str, Any]],
        news: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Make trading decisions using Gemini"""
        
        # Prepare context for the model
        context = self._prepare_context(market_data, portfolio_state, memories, news)
        
        try:
            # Get model's response
            response = self.chat.send_message(json.dumps(context))
            
            # Parse and validate decisions
            decisions = self._parse_decisions(response.text)
            
            # Apply risk management rules
            decisions = self._apply_risk_rules(decisions, portfolio_state)
            
            return decisions
            
        except Exception as e:
            logger.error(f"Error getting LLM decision: {str(e)}")
            return {}
            
    def _prepare_context(
        self,
        market_data: Dict[str, Any],
        portfolio_state: Dict[str, Any],
        memories: List[Dict[str, Any]],
        news: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepare context for the LLM"""
        
        # Format current market data
        current_data = []
        for stock_data in market_data["data"]:
            current_data.append({
                "symbol": stock_data["Symbol"],
                "price": stock_data["Close"],
                "daily_return": f"{stock_data['Daily_Return']*100:.1f}%",
                "rsi": stock_data["RSI"],
                "trend": "bullish" if stock_data["20d_MA"] > stock_data["50d_MA"] else "bearish",
                "volume_signal": "high" if stock_data["Volume"] > stock_data["Volume_MA"] * 1.5 else "normal"
            })
            
        # Format portfolio state
        positions = []
        for symbol, pos in portfolio_state["positions"].items():
            positions.append({
                "symbol": symbol,
                "quantity": pos["quantity"],
                "entry_price": pos["price"],
                "current_price": pos["current_price"],
                "return": f"{pos['return']*100:.1f}%"
            })
            
        # Format memories
        relevant_memories = [mem["text"] for mem in memories]
        
        # Format news
        recent_news = []
        for article in news:
            recent_news.append({
                "title": article["title"],
                "content": article["content"],
                "date": article["date"]
            })
            
        return {
            "task": "make_trading_decisions",
            "current_market_data": current_data,
            "portfolio": {
                "cash": portfolio_state["cash"],
                "total_value": portfolio_state["total_value"],
                "returns": f"{portfolio_state['returns']*100:.1f}%",
                "positions": positions
            },
            "relevant_memories": relevant_memories,
            "recent_news": recent_news
        }
        
    def _parse_decisions(self, response: str) -> Dict[str, Dict[str, Any]]:
        """Parse LLM response into trading decisions"""
        try:
            # Try to parse as JSON first
            decisions = json.loads(response)
            if isinstance(decisions, dict):
                return decisions
        except:
            pass
            
        # If JSON parsing fails, try to extract structured decisions from text
        decisions = {}
        lines = response.split("\n")
        current_symbol = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for symbol headers
            if line.isupper() and len(line) < 20:
                current_symbol = line
                continue
                
            # Look for action keywords
            if current_symbol:
                if "buy" in line.lower():
                    # Try to extract quantity and price
                    import re
                    qty_match = re.search(r"(\d+)\s+shares", line)
                    price_match = re.search(r"₹\s*(\d+\.?\d*)", line)
                    
                    if qty_match and price_match:
                        decisions[current_symbol] = {
                            "action": "buy",
                            "quantity": int(qty_match.group(1)),
                            "price": float(price_match.group(1)),
                            "reason": line
                        }
                        
                elif "sell" in line.lower():
                    qty_match = re.search(r"(\d+)\s+shares", line)
                    price_match = re.search(r"₹\s*(\d+\.?\d*)", line)
                    
                    if qty_match and price_match:
                        decisions[current_symbol] = {
                            "action": "sell",
                            "quantity": int(qty_match.group(1)),
                            "price": float(price_match.group(1)),
                            "reason": line
                        }
                        
        return decisions
        
    def _apply_risk_rules(
        self,
        decisions: Dict[str, Dict[str, Any]],
        portfolio_state: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Apply risk management rules to decisions"""
        filtered_decisions = {}
        available_cash = float(portfolio_state["cash"])
        portfolio_value = float(portfolio_state["total_value"])
        position_size_limit = portfolio_value * 0.2  # 20% limit
        
        for symbol, decision in decisions.items():
            try:
                if decision["action"] == "buy":
                    # Check if we have enough cash
                    cost = decision["quantity"] * decision["price"]
                    if cost > available_cash:
                        continue
                        
                    # Check position size limit
                    if cost > position_size_limit:
                        # Adjust quantity to meet limit
                        max_quantity = int(position_size_limit / decision["price"])
                        if max_quantity < 100:  # Minimum 100 shares
                            continue
                        decision["quantity"] = min(max_quantity, 1000)  # Cap at 1000 shares
                        
                    available_cash -= decision["quantity"] * decision["price"]
                    
                filtered_decisions[symbol] = decision
                
            except (KeyError, TypeError) as e:
                logger.warning(f"Error applying risk rules for {symbol}: {str(e)}")
                continue
                
        return filtered_decisions 