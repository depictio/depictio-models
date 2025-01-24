# depictio_cli/logging.py
import logging
from colorlog import ColoredFormatter

# Initialize logger without handlers
logger = logging.getLogger("depictio-models")
logger.propagate = False  # Prevent propagation to root logger

def setup_logging(verbose: bool = False) -> logging.Logger:
    global logger
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    if verbose:
        formatter = ColoredFormatter(
            "%(log_color)s%(asctime)s%(reset)s - %(name)s - %(log_color)s%(levelname)s%(reset)s - %(filename)s - %(funcName)s - line %(lineno)d - %(message)s",
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)
        
    return logger