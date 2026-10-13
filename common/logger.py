import logging
from logging.handlers import RotatingFileHandler
LOG_FILE = "logs/test.log"

logging.basicConfig(
    level=logging.INFO,
    force=True,
    format="%(asctime)s %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            LOG_FILE, 
            maxBytes=1024*1024,
            backupCount=3,
            encoding="utf-8"
            )
    ]
)