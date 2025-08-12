from enum import Enum

class LogLevelEnum(str, Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class SkaldEnvEnum(str, Enum):
    DEV = "DEV"
    PRODUCTION = "PRODUCTION"

class SkaldModeEnum(str, Enum):
    EDGE = "edge"
    NODE = "node"