from enum import Enum

class LogLevelEnum(Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class SkaldEnvEnum(Enum):
    DEV = "DEV"
    PRODUCTION = "PRODUCTION"