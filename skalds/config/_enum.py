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
    SINGLE_PROCESS = "single_process"

class SystemControllerModeEnum(str, Enum):
    """Enumeration for SystemController operational modes."""
    CONTROLLER = "CONTROLLER"      # API only
    MONITOR = "MONITOR"           # API + monitoring + dashboard
    DISPATCHER = "DISPATCHER"     # Full system (API + monitoring + dispatching)

    @classmethod
    def list(cls) -> list[str]:
        """Return a list of all mode values."""
        return [c.value for c in cls]


class DispatcherStrategyEnum(str, Enum):
    """Enumeration for task assignment strategies."""
    LEAST_TASKS = "LEAST_TASKS"    # Assign to Skalds with fewest tasks
    ROUND_ROBIN = "ROUND_ROBIN"    # Round-robin assignment
    RANDOM = "RANDOM"              # Random assignment

    @classmethod
    def list(cls) -> list[str]:
        """Return a list of all strategy values."""
        return [c.value for c in cls]