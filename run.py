#!/usr/bin/env python3
import click
from loguru import logger
import toml
from pathlib import Path
from puppy.core.simulation import Simulation
from puppy.utils.config import load_config

@click.group()
def cli():
    """FinMem India - LLM Trading Agent for Indian Stock Market"""
    pass

@cli.command()
@click.option(
    "--config-path",
    "-cp",
    default="config/config.toml",
    help="Path to configuration file",
)
@click.option(
    "--mode",
    "-m",
    default="train",
    type=click.Choice(["train", "test", "backtest"]),
    help="Run mode: train or test",
)
@click.option(
    "--checkpoint-path",
    "-ckp",
    default="data/checkpoints",
    help="Path to save/load checkpoints",
)
@click.option(
    "--result-path",
    "-rp",
    default="data/results",
    help="Path to save results",
)
def run(config_path: str, mode: str, checkpoint_path: str, result_path: str):
    """Start the trading simulation"""
    logger.info(f"Starting FinMem India in {mode} mode")
    
    # Load configuration
    config = load_config(config_path)
    
    # Create directories if they don't exist
    Path(checkpoint_path).mkdir(parents=True, exist_ok=True)
    Path(result_path).mkdir(parents=True, exist_ok=True)
    
    # Initialize and run simulation
    sim = Simulation(
        config=config,
        mode=mode,
        checkpoint_path=checkpoint_path,
        result_path=result_path
    )
    sim.run()

if __name__ == "__main__":
    cli() 