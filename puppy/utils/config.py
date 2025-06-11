import toml
from typing import Dict, Any
from loguru import logger

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load and validate configuration from TOML file
    
    Args:
        config_path: Path to config file
        
    Returns:
        Validated configuration dictionary
    """
    try:
        # Load config file
        with open(config_path, "r") as f:
            config = toml.load(f)
        
        # Validate required sections
        required_sections = ["market", "chat", "agent", "memory", "trading"]
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required section '{section}' in config")
        
        # Validate market section
        market = config["market"]
        required_market = ["symbols", "data_start_date", "data_end_date"]
        for field in required_market:
            if field not in market:
                raise ValueError(f"Missing required field '{field}' in market config")
            
        # Validate trading section
        trading = config["trading"]
        required_trading = ["initial_capital", "position_size_limit", "stop_loss", "take_profit"]
        for field in required_trading:
            if field not in trading:
                raise ValueError(f"Missing required field '{field}' in trading config")
                
        # Validate memory section
        memory = config["memory"]
        required_memory = ["short_term_capacity", "long_term_capacity"]
        for field in required_memory:
            if field not in memory:
                raise ValueError(f"Missing required field '{field}' in memory config")
                
        logger.info("Configuration loaded and validated successfully")
        return config
        
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        raise 