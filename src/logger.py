import logging
from src.config import Config

# Setup logger configuration
log_level = logging.DEBUG if getattr(Config, "DEBUG", False) else logging.WARNING

# Setup basic configuration
logging.basicConfig(
    level=log_level,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger("CricketIQ")
