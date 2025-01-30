#!/usr/bin/env python3

VERSION = "v0.1.0/2025-02-22"
# Developed by Chad Kluck with AI assistance from Amazon Q Developer

# Usage Example:

# from lib.logger import ScriptLogger, log_info, log_warn, log_error

# # Setup logger at the start of your script
# ScriptLogger.setup('your-script-name')

# # ConsoleAndLog can be used to display the SAME message to BOTH the console and log file
# ConsoleAndLog.info("Starting process...")
# try:
#     # do something
#     pass
# except Exception as e:
#     ConsoleAndLog.error("Process failed", e)

import logging
import sys
from pathlib import Path
from typing import Optional, Callable

class ScriptLogger:
    _instance = None
    _ERROR_MSG = "Logger not initialized. Call ScriptLogger.setup() first"
    
    def __init__(self):
        raise RuntimeError("Use ScriptLogger.setup() or ScriptLogger.get_logger()")
    
    @classmethod
    def setup(cls, script_name: str, log_dir: str = "scripts/logs") -> logging.Logger:
        """Initialize the logger for a specific script
        
        Args:
            script_name: Name of the script (e.g., 'deploy', 'build')
            log_dir: Directory where log files should be stored
        
        Returns:
            logging.Logger: Configured logger instance
        """
        if cls._instance is None:
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            
            logger = logging.getLogger(script_name)
            logger.setLevel(logging.INFO)
            
            if not logger.handlers:
                cls._add_handlers(logger, log_path, script_name)
            
            cls._instance = logger
        
        return cls._instance
    
    @classmethod
    def _add_handlers(cls, logger: logging.Logger, log_path: Path, script_name: str) -> None:
        """Add file and console handlers to the logger"""
        # File handler with detailed formatting
        file_handler = logging.FileHandler(log_path / f"script-{script_name}.log")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(file_handler)
        
        # Console handler with simplified formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(console_handler)
    
    @classmethod
    def get_logger(cls) -> Optional[logging.Logger]:
        """Get the configured logger instance"""
        return cls._instance

class ConsoleAndLog:
    @staticmethod
    def _log_message(level_func: Callable, message: str, e: Optional[Exception] = None) -> None:
        """Generic logging function"""
        logger = ScriptLogger.get_logger()
        if not logger:
            raise RuntimeError(ScriptLogger._ERROR_MSG)
        
        if e:
            level_func(f"{message} ERR: {str(e)}")
        else:
            level_func(message)
    
    @classmethod
    def info(cls, message: str) -> None:
        """Log an info message"""
        logger = ScriptLogger.get_logger()
        if not logger:
            raise RuntimeError(ScriptLogger._ERROR_MSG)
        cls._log_message(logger.info, message)
    
    @classmethod
    def warning(cls, message: str, e: Optional[Exception] = None) -> None:
        """Log a warning message"""
        logger = ScriptLogger.get_logger()
        if not logger:
            raise RuntimeError(ScriptLogger._ERROR_MSG)
        cls._log_message(logger.warning, message, e)
    
    @classmethod
    def error(cls, message: str, e: Optional[Exception] = None) -> None:
        """Log an error message"""
        logger = ScriptLogger.get_logger()
        if not logger:
            raise RuntimeError(ScriptLogger._ERROR_MSG)
        cls._log_message(logger.error, message, e)

# Convenience functions
def log_info(message: str) -> None:
    """Convenience function for info logging"""
    ConsoleAndLog.info(message)

def log_warn(message: str, e: Optional[Exception] = None) -> None:
    """Convenience function for warning logging"""
    ConsoleAndLog.warning(message, e)

def log_error(message: str, e: Optional[Exception] = None) -> None:
    """Convenience function for error logging"""
    ConsoleAndLog.error(message, e)
