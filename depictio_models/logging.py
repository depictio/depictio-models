import logging
from colorlog import ColoredFormatter

# Create a logger
logger = logging.getLogger("depictio-models")
logger.setLevel(logging.DEBUG)

# Create a colored formatter
formatter = ColoredFormatter(
    "%(log_color)s%(asctime)s%(reset)s | %(cyan)s%(name)s%(reset)s | %(green)s%(levelname)s%(reset)s | %(yellow)s%(funcName)s:%(lineno)d%(reset)s | %(message)s",
    datefmt=None,
    reset=True,
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red,bg_white',
    },
    secondary_log_colors={},
    style='%'
)

# Create a console handler and set the formatter
handler = logging.StreamHandler()
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)