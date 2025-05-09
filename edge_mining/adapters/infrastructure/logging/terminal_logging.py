"""The terminal log."""

import logging
import sys
import json
import traceback
from pprint import pformat

from edge_mining.shared.logging.port import LoggerPort

class TerminalLogger(LoggerPort):
    """Terminal logger class."""

    def __init__(self, name="", LOG_LEVEL="INFO"):
        self.name = name
        self.LOG_LEVEL = LOG_LEVEL
        self.default_log()

    def show_log_level(self, record):
        """Allows to show stuff in the log based on the global setting."""
        return record["level"].no >= self.logger.level(self.LOG_LEVEL).no

    def default_log(self):
        """Set the same debug level to all the project dependencies."""

        logging.basicConfig(
            level=self.LOG_LEVEL,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)] # Log to console
        )
        
        self.logger = logging.getLogger(self.name)

    def __call__(self, msg, level="DEBUG"):
        """Alias of self.log()"""
        self.log(msg, level)

    def debug(self, msg):
        """Logs a DEBUG message"""
        self.log(msg, level="DEBUG")

    def info(self, msg):
        """Logs an INFO message"""
        self.log(msg, level="INFO")

    def warning(self, msg):
        """Logs a WARNING message"""
        self.log(msg, level="WARNING")

    def error(self, msg):
        """Logs an ERROR message"""
        self.log(msg, level="ERROR")

        # Only print the traceback if an exception handler is being executed
        if sys.exc_info()[0] is not None:
            traceback.print_exc()

    def critical(self, msg):
        """Logs a CRITICAL message"""
        self.log(msg, level="CRITICAL")
        
        # Only print the traceback if an exception handler is being executed
        if sys.exc_info()[0] is not None:
            traceback.print_exc()

    def log(self, msg, level="DEBUG"):
        """Log a message"""

        # prettify
        if isinstance(msg, str):
            pass
        elif type(msg) in [dict, list]:  # TODO: should be recursive
            try:
                msg = json.dumps(msg, indent=4)
            except Exception:
                pass
        else:
            msg = pformat(msg)
            
        # Convert level string to log level
        if level == "DEBUG":
            level = logging.DEBUG
        elif level == "INFO":
            level = logging.INFO
        elif level == "WARNING":
            level = logging.WARNING
        elif level == "ERROR":
            level = logging.ERROR
        elif level == "CRITICAL":
            level = logging.CRITICAL

        # actual log
        lines = msg.split("\n")
        for line in lines:
            self.logger.log(level=level, msg=line)

    def welcome(self):
        """Welcome message in the terminal."""

        print("\n\n")
        with open("edge_mining/welcome.txt", "r") as f:
            print(f.read())
        print("\n\n")

        print("Hey! 👋 I'm Edge Mining. Mine your energy! ⚡⛏️")
        print("\n\n")

    def shutdown(self):
        """Sure that log are written to the file before exiting."""

        # Flush the logger
        for handler in self.logger.handlers:
            handler.flush()

        # Close the logger
        for handler in self.logger.handlers:
            handler.close()

        # Print a goodbye message
        print("Shutting down...")
        print("Goodbye! 👋​")

    def log_examples(self):
        """Log examples for the log engine."""

        for c in [self, "Hello from logging!", {"ready", "set", "go"}, [1, 4, "finchelabarcavalascialandare"], {"a": 1, "b": {"c": 2}}]:
            self.debug(c)
            self.info(c)
            self.warning(c)
            self.error(c)
            self.critical(c)

        def intentional_error():
            print(42/0)

        try:
            intentional_error()
        except Exception:
            self.error("This error is just for demonstration purposes. Don't worry, I got it covered! 😉")