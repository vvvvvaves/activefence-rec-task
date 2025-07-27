import logging
import os
from datetime import datetime

def setup_perspective_logger():
    """
    Setup logger for Perspective API exceptions.
    Creates a new log file for every run with timestamp.
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('perspective_api')
    logger.setLevel(logging.ERROR)
    
    # Clear any existing handlers to avoid duplicate logging
    logger.handlers.clear()
    
    # Create file handler with timestamp for each run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f'perspective_errors_{timestamp}.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.ERROR)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - POST_ID: %(post_id)s - TEXT_LENGTH: %(text_length)s - ERROR: %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    return logger

def log_perspective_error(logger, post_id, text_length, error_message, error_details=None):
    """
    Log Perspective API error with structured information.
    
    Args:
        logger: The logger instance
        post_id: ID of the post/conversation
        text_length: Length of the text in characters
        error_message: Main error message
        error_details: Additional error details (optional)
    """
    extra_info = {
        'post_id': post_id,
        'text_length': text_length
    }
    
    if error_details:
        full_message = f"{error_message} | Details: {error_details}"
    else:
        full_message = error_message
    
    logger.error(full_message, extra=extra_info) 