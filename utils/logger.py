"""Logging functionality for the flash sintering control system.
"""
import logging
import os
from datetime import datetime

def setup_logger(name):
    """Set up and return a logger instance"""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Create handlers
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'flash_sinter_{timestamp}.log')
    
    file_handler = logging.FileHandler(log_file)
    console_handler = logging.StreamHandler()
    
    # Create formatters and add it to handlers
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(log_format)
    console_handler.setFormatter(log_format)
    
    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

class Logger:
    """Logger class for the flash sintering control system.
    """
    def __init__(self, log_file=None):
        """Initialize logger.
        """
        if log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"flash_sintering_{timestamp}.log"

        # Create logs directory if it doesn't exist
        if not os.path.exists("logs"):
            os.makedirs("logs")
        log_file = os.path.join("logs", log_file)

        # Configure logger
        self.logger = logging.getLogger("flash_sintering")
        self.logger.setLevel(logging.DEBUG)

        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def debug(self, message):
        """Log debug message.
        """
        self.logger.debug(message)

    def info(self, message):
        """Log info message.
        """
        self.logger.info(message)

    def warning(self, message):
        """Log warning message.
        """
        self.logger.warning(message)

    def error(self, message):
        """Log error message.
        """
        self.logger.error(message)

    def critical(self, message):
        """Log critical message.
        """
        self.logger.critical(message)

# Create global logger instance
logger = Logger() 