# FinMem India

An adaptation of the FinMem LLM Trading Agent for the Indian stock market, focusing on Nifty 50 stocks.

## Overview

FinMem India is a Large Language Model (LLM) based trading agent that uses a layered memory architecture to make informed trading decisions in the Indian stock market. The agent maintains both short-term and long-term memories of market data, technical indicators, and trading history to make decisions based on historical context and current market conditions.

Recent advancements in Large Language Models (LLMs) have exhibited notable efficacy in question-answering (QA) tasks across diverse domains. Their prowess in integrating extensive web knowledge has fueled interest in developing LLM-based autonomous agents. While LLMs are efficient in decoding human instructions and deriving solutions by holistically processing historical inputs, transitioning to purpose-driven agents requires a supplementary rational architecture to process multi-source information, establish reasoning chains, and prioritize critical tasks. Addressing this, we introduce FinMem, a novel LLM-based agent framework devised for financial decision-making, encompassing three core modules: Profiling, to outline the agent's characteristics; Memory, with layered processing, to aid the agent in assimilating realistic hierarchical financial data; and Decision-making, to convert insights gained from memories into investment decisions. Notably, FinMem's memory module aligns closely with the cognitive structure of human traders, offering robust interpretability and real-time tuning. Its adjustable cognitive span allows for the retention of critical information beyond human perceptual limits, thereby enhancing trading outcomes. This framework enables the agent to self-evolve its professional knowledge, react agilely to new investment cues, and continuously refine trading decisions in the volatile financial environment. We first compare FinMem with various algorithmic agents on a scalable real-world financial dataset, underscoring its leading trading performance in stocks and funds. We then fine-tuned the agent's perceptual spans to achieve a significant trading performance. Collectively, FinMem presents a cutting-edge LLM agent framework for automated trading, boosting cumulative investment returns.



## Features

- Focused on Nifty 50 stocks trading
- Uses Gemini Flash 2.0 for decision making
- Implements layered memory architecture (short-term and long-term)
- Real-time technical indicator calculations
- Risk management with position size limits
- Detailed transaction logging and performance tracking

## Requirements

- Python 3.10 or higher
- Poetry for dependency management
- Gemini API Key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/leee1337/finmem-india.git
cd finmem-india
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Create a `.env` file with your OpenAI API key:
```bash
echo "GEMINI_API_KEY=your-api-key-here" > .env
```

## Configuration

The agent can be configured through the `config/config.toml` file. Key configuration options include:

- Market parameters (symbols, date range)
- Trading parameters (initial capital, position limits)
- Agent personality and risk preferences
- Memory configuration
- LLM settings

## Usage
0. Main program
``` bash
python trading_system.py
```
1. Training mode (builds agent's memory):
```bash
python run python run.py --mode train
```

2. Testing mode (live trading simulation):
```bash
python run python run.py --mode test
```


## Project Structure

```
finmem-india/
├── config/
│   └── config.toml         # Configuration files
├── data/
│   ├── raw/               # Raw market data
│   └── processed/         # Processed data and results
├── puppy/
│   ├── core/             # Core simulation logic
│   ├── models/           # Trading agent and memory models
│   └── utils/            # Utility functions and classes
├── pyproject.toml        # Poetry dependencies
└── run.py               # Main entry point
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

This project is based on the original FinMem project by [pipiku915](https://github.com/pipiku915/finmem-llm-stocktrading). 

Market Focus:
FinMem: US stock market
FinMem India: Indian stock market, specifically Nifty 50 stocks
Data Sources:
FinMem: Uses US market data providers
FinMem India:
Uses MoneyControl for news
NSEPy for Indian market data
YFinance with .NS suffix for real-time data
Currency and Values:
FinMem: Works in USD
FinMem India: Works in INR (₹)
Initial capital: ₹10 Lakhs
Position sizing adapted for Indian market volumes
Trading Hours:
FinMem: US market hours
FinMem India: Indian market hours (9:15 AM - 3:30 PM IST)
Stock Selection:
FinMem: US stocks
FinMem India: Nifty 50 components with .NS suffix
Apply to trades.csv
]
News Integration:
FinMem: Uses US news sources
FinMem India:
Integrated MoneyControl news scraping
Stock-specific news tracking for Indian companies
Search functionality adapted for Indian market news
Risk Management:
FinMem: Generic risk parameters
FinMem India: Adapted for Indian market volatility
20% position size limit
5% stop loss
15% take profit
Minimum 100 shares per trade
Maximum 1000 shares per position
Technical Indicators:
Both use similar indicators but FinMem India has:
Volume analysis specific to Indian market patterns
RSI ranges adjusted for Indian market volatility (30-70)
Moving averages (20 & 50 day) for trend following
Memory Architecture:
Both use layered memory but FinMem India has:
Short-term capacity: 10 events
Long-term capacity: 100 events
Relevance threshold: 0.75
Focus on Indian market patterns and behaviors
Trading Rules:
FinMem India adds:
Minimum 5-day holding period
Maximum 30% of available cash per position
High volume confirmation for take-profit
Trend reversal exits only in profit
Logging and Reporting:
FinMem India:
Trades logged in INR
Indian market-specific metrics
MoneyControl news references in trade reasons
Dependencies:
Added Indian market specific packages:
Apply to trades.csv
data
The core architecture remains similar, but FinMem India has been substantially modified to work with Indian market characteristics, data sources, and trading patterns. 

Now your system has been updated with:
Layered Memory Architecture:
Short-term memory for recent market events (100 entries)
Long-term memory for historical patterns (1000 entries)
Vector-based retrieval using ChromaDB
Automatic memory consolidation based on importance
RAG (Retrieval Augmented Generation):
Uses sentence-transformers for semantic search
Combines relevance and importance scores
Retrieves both short-term and long-term memories
Contextual memory retrieval based on market conditions
Gemini 2.0 Flash Integration:
Advanced decision making using market data, news, and memories
Personality-driven trading style
Risk management rules enforcement
Natural language reasoning about market conditions
The system now works as follows:
When market data arrives:
Data is processed and stored in short-term memory
Important patterns are automatically moved to long-term memory
Vector embeddings are created for efficient retrieval
When making trading decisions:
Current market conditions are analyzed
Relevant memories are retrieved using RAG
News sentiment is considered
Gemini 2.0 Flash makes the final decision
Risk management rules are applied
Configuration:
Memory capacities and thresholds in config.toml
Trading parameters and risk limits
Agent personality and style settings
Gemini model parameters