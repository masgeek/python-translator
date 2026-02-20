import sys
from datetime import datetime
from loguru import logger


class LoggingConfig:
    """
    Central logging configuration for the application.
    Call LoggingConfig.setup(verbose=True/False) once at startup.
    """

    @staticmethod
    def setup(verbose: bool = False, log_prefix: str = "app") -> None:
        logger.remove()

        level = "DEBUG" if verbose else "INFO"

        # Console logger
        logger.add(
            sys.stdout,
            colorize=True,
            level=level,
            format="<green>{time:HH:mm:ss}</green> | "
                   "<level>{level:<8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "{message}"
        )

        # File logger
        logger.add(
            f"{log_prefix}_{datetime.now().strftime('%Y%m%d')}.log",
            encoding="utf-8",
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | "
                   "{level:<8} | "
                   "{name}:{function}:{line} - {message}",
            rotation="10 MB",  # auto rotate
            retention="7 days",  # keep logs 7 days
            compression="zip"  # compress old logs
        )
