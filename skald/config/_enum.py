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

class SystemControllerModeEnum(str, Enum):
    """Enumeration for SystemController operational modes."""
    CONTROLLER = "controller"      # API only
    MONITOR = "monitor"           # API + monitoring + dashboard  
    DISPATCHER = "dispatcher"     # Full system (API + monitoring + dispatching)

    @classmethod
    def list(cls) -> list[str]:
        """Return a list of all mode values."""
        return [c.value for c in cls]