"""
llmbrick.utils.logging
----------------------
Pretty-Loguru 封裝，提供全域 logger、decorator 與動態配置功能。
需先安裝 pretty-loguru: pip install pretty-loguru
"""
from pretty_loguru import LoggerConfig, create_logger, configure_logger, EnhancedLogger
from skalds.config._enum import LogLevelEnum
from skalds.config.systemconfig import SystemConfig

config = LoggerConfig(level="INFO", rotation="1 day", retention="7 days")

# 預設全域 logger
logger = create_logger()

def init_logger(logger_name: str, level: LogLevelEnum = "INFO", log_path = "logs", process_id = "", rotation = "20"):
    global logger
    format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss} </green> | "
        "<level>{level} " + process_id + " {process} </level>| "
        "<cyan>{file}:{function}:{line}</cyan> - <level>{message}</level>"
    )

    logger_config = LoggerConfig(
        name=logger_name,
        log_path=log_path,
        level=level,
        rotation=f"{rotation}MB",  # Rotate log file when it reaches 20 MB
        logger_format=format,
    )

    configure_logger(
        logger_instance=logger,
        config=logger_config
    )