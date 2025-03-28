import logging
import json
import os
from pathlib import Path

def setup_logger(name: str, config_path: str = None) -> logging.Logger:
    """
    Set up a logger with the specified name and configuration.
    
    Args:
        name (str): Name of the logger
        config_path (str, optional): Path to the config file. Defaults to None.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:  # Return if logger is already configured
        return logger
        
    # Default configuration
    log_config = {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    }
    
    # Load configuration from file if provided
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            if 'logging' in config:
                log_config.update(config['logging'])
    
    # Create formatter
    formatter = logging.Formatter(log_config['format'])
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Create file handler
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / f"{name}.log")
    file_handler.setFormatter(formatter)
    
    # Set log level
    logger.setLevel(getattr(logging, log_config['level'].upper()))
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger 