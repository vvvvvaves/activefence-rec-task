import logging
import logging.handlers
import os
import threading
import queue
from datetime import datetime

class ThreadSafeLogger:
    """
    Thread-safe logger implementation using QueueHandler and QueueListener pattern.
    This is the recommended approach for multi-threaded logging in Python.
    """
    
    def __init__(self):
        self.log_queue = queue.Queue()
        self.logger = None
        self.listener = None
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup the logger with QueueHandler and QueueListener."""
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.path.dirname(__file__))
        os.makedirs(log_dir, exist_ok=True)
        
        # Create timestamp for log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f'gather_operations_{timestamp}.log')
        
        # Create the main logger
        self.logger = logging.getLogger('gather_operations')
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Create QueueHandler - this is thread-safe
        queue_handler = logging.handlers.QueueHandler(self.log_queue)
        self.logger.addHandler(queue_handler)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - THREAD: %(threadName)s - SUBREDDIT: %(subreddit)s - LEVEL: %(levelname)s - MESSAGE: %(message)s'
        )
        
        # Create FileHandler for the listener
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # Create QueueListener - this runs in a separate thread and handles all file I/O
        self.listener = logging.handlers.QueueListener(
            self.log_queue, 
            file_handler,
            respect_handler_level=True
        )
        
        # Start the listener thread
        self.listener.start()
        
        print(f"Thread-safe logger initialized. Log file: {log_file}")
    
    def stop(self):
        """Stop the logger and listener."""
        if self.listener:
            self.listener.stop()
            print("Logger stopped.")
    
    def get_logger(self):
        """Get the thread-safe logger instance."""
        return self.logger

# Global logger instance
_global_logger = None
_logger_lock = threading.Lock()

def setup_gather_logger():
    """
    Setup and return a thread-safe logger instance.
    Uses singleton pattern with proper thread safety.
    """
    global _global_logger
    
    if _global_logger is None:
        with _logger_lock:
            if _global_logger is None:
                _global_logger = ThreadSafeLogger()
    
    return _global_logger.get_logger()

def stop_gather_logger():
    """Stop the global logger instance."""
    global _global_logger
    if _global_logger:
        _global_logger.stop()

def log_gather_error(logger, subreddit, error_message, error_details=None):
    """
    Log gather operation error with structured information.
    
    Args:
        logger: The logger instance
        subreddit: Name of the subreddit being processed
        error_message: Main error message
        error_details: Additional error details (optional)
    """
    extra_info = {
        'subreddit': subreddit
    }
    
    if error_details:
        full_message = f"{error_message} | Details: {error_details}"
    else:
        full_message = error_message
    
    logger.error(full_message, extra=extra_info)

def log_gather_info(logger, subreddit, message):
    """
    Log gather operation info with structured information.
    
    Args:
        logger: The logger instance
        subreddit: Name of the subreddit being processed
        message: Information message
    """
    extra_info = {
        'subreddit': subreddit
    }
    
    logger.info(message, extra=extra_info)

def log_gather_warning(logger, subreddit, message):
    """
    Log gather operation warning with structured information.
    
    Args:
        logger: The logger instance
        subreddit: Name of the subreddit being processed
        message: Warning message
    """
    extra_info = {
        'subreddit': subreddit
    }
    
    logger.warning(message, extra=extra_info) 