"""
Logging Configuration Module
Production-grade logging with file and console handlers
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import colorlog
from .config import config

class LoggerManager:
    """Manages application logging"""
    
    def __init__(self):
        self.loggers = {}
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration"""
        # Ensure logs directory exists
        config.LOGS_DIR.mkdir(exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = config.LOGS_DIR / f"bdd_generator_{timestamp}.log"
        
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, config.LOG_LEVEL))
        
        # Remove existing handlers
        root_logger.handlers = []
        
        # Console handler with colors
        console_handler = colorlog.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger instance"""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
        return self.loggers[name]

# Global logger manager
logger_manager = LoggerManager()

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logger_manager.get_logger(name)