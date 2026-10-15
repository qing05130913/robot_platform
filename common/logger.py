import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "test.log")

# 确保日志目录存在：logs/ 已被 .gitignore 排除，新 clone 下可能不存在，
# 若不创建，首次写入日志会抛 FileNotFoundError。
os.makedirs(LOG_DIR, exist_ok=True)

# 幂等配置：仅当根 logger 尚无 handler 时才配置。
# 不使用 force=True，避免本模块被重复导入时覆盖其它 logging 配置。
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(
                LOG_FILE,
                maxBytes=1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            ),
        ],
    )
