"""Log Port"""

from abc import ABC, abstractmethod


class LoggerPort(ABC):
    """Port for the Logger."""

    @abstractmethod
    def show_log_level(self, record):
        """Allows to show stuff in the log based on the global setting."""
        raise NotImplementedError

    @abstractmethod
    def default_log(self):
        """Set the same debug level to all the project dependencies."""
        raise NotImplementedError

    @abstractmethod
    def debug(self, msg):
        """Logs a DEBUG message"""
        raise NotImplementedError

    @abstractmethod
    def info(self, msg):
        """Logs an INFO message"""
        raise NotImplementedError

    @abstractmethod
    def warning(self, msg):
        """Logs a WARNING message"""
        raise NotImplementedError

    @abstractmethod
    def error(self, msg):
        """Logs an ERROR message"""
        raise NotImplementedError

    @abstractmethod
    def critical(self, msg):
        """Logs a CRITICAL message"""
        raise NotImplementedError

    @abstractmethod
    def log(self, msg, level="DEBUG"):
        """Log a message"""
        raise NotImplementedError

    @abstractmethod
    def welcome(self):
        """Welcome message in the terminal."""
        raise NotImplementedError

    @abstractmethod
    def shutdown(self):
        """Sure that log are written to the file before exiting."""
        raise NotImplementedError

    @abstractmethod
    def log_examples(self):
        """Log examples for the log engine."""
        raise NotImplementedError
