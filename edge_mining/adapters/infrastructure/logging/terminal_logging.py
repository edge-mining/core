"""The terminal log."""

import json
import sys
import traceback
from pprint import pformat

from loguru import logger

from edge_mining.shared.logging.port import LoggerPort


class TerminalLogger(LoggerPort):
    """Terminal logger class."""

    def __init__(self, name="", log_level="INFO"):
        self.name = name
        self.log_level = log_level
        self.default_log()

    def show_log_level(self, record):
        """Allows to show stuff in the log based on the global setting."""
        pass

    def default_log(self):
        """Set the same debug level to all the project dependencies."""
        logger.remove()

        logger.add(
            sys.stdout,
            level=self.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            colorize=True,
            backtrace=False,
            diagnose=True,
        )

        # logging.basicConfig(
        #     level=self.log_level,
        #     format='%(asctime)s - %(levelname)s - %(message)s',
        #     handlers=[logging.StreamHandler(sys.stdout)] # Log to console
        # )

        # self.logger = logging.getLogger(self.name)

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
                msg = msg
        else:
            msg = pformat(msg)

        log_method = getattr(logger, level.lower(), logger.debug)  # Default to debug if level is unknown

        log_method(msg)

    def welcome(self):
        """Welcome message in the terminal."""

        print("\n\n")
        with open("edge_mining/welcome.txt", "r", encoding="utf-8") as f:
            print(f.read())
        print("\n\n")

        print("Hey! 👋 I'm Edge Mining. Mine your energy! ⚡⛏️")
        print("\n\n")

    def shutdown(self):
        """Sure that log are written to the file before exiting."""

        logger.complete()

        # Print a goodbye message
        print("Shutting down...")
        print("Goodbye! 👋")

    def log_examples(self):
        """Log examples for the log engine."""

        for c in [
            self,
            "Hello from logging!",
            {"ready", "set", "go"},
            [1, 4, "finchelabarcavalascialandare"],
            {"a": 1, "b": {"c": 2}},
        ]:
            self.debug(c)
            self.info(c)
            self.warning(c)
            self.error(c)
            self.critical(c)

        def intentional_error():
            print(42 / 0)

        try:
            intentional_error()
        except Exception:
            self.error("This error is just for demonstration purposes. Don't worry, I got it covered! 😉")
