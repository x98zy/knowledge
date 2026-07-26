import logging
import os
from logging.handlers import RotatingFileHandler


class FastapiLogger:
    """FastAPI Logger extension, manages global logger instance."""

    def __init__(self) -> None:
        self._logger: logging.Logger | None = None
        self.init()

    def init(self) -> None:
        """Initialize logger instance (called synchronously at module import time)."""
        logger = logging.getLogger("fastapi-app")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        if logger.handlers:
            self._logger = logger
            return

        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        os.makedirs(log_dir, exist_ok=True)

        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        numeric_level = getattr(logging, log_level, logging.INFO)
        logger.setLevel(numeric_level)

        log_format = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s"
        )

        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)

        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "app.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)

        self._logger = logger

    @property
    def logger(self) -> logging.Logger:
        """Get logger instance."""
        if self._logger is None:
            raise RuntimeError("Logger not initialized, call logger.init() first.")
        return self._logger

    def debug(self, message: str, *args, **kwargs) -> None:
        """Log debug level message."""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """Log info level message."""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """Log warning level message."""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        """Log error level message."""
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        """Log critical level message."""
        self.logger.critical(message, *args, **kwargs)


logger = FastapiLogger()

__all__ = ["logger"]