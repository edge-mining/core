"""
Telegram adapter (Implementation of Port) that uses telegram
as notification sender for Edge Mining Application
"""

from typing import Optional

import re

import telegram
from telegram.constants import ParseMode
from telegram.error import TelegramError

from edge_mining.domain.notification.exceptions import NotifierConfigurationError
from edge_mining.domain.notification.ports import NotificationPort
from edge_mining.shared.interfaces.config import Configuration
from edge_mining.shared.adapter_configs.notification import TelegramNotificationConfig
from edge_mining.shared.external_services.ports import ExternalServicePort
from edge_mining.shared.interfaces.factories import NotificationAdapterFactory
from edge_mining.shared.logging.port import LoggerPort


class TelegramNotifierFactory(NotificationAdapterFactory):
    """
    Creates a factory for Telegram notification adapter.

    This factory aims to simplifying the building of Telegram.
    """

    def create(
        self,
        config: Optional[Configuration],
        logger: Optional[LoggerPort],
        external_service: Optional[ExternalServicePort],
    ) -> NotificationPort:
        """Create a notification adapter"""

        if not isinstance(config, TelegramNotificationConfig):
            raise NotifierConfigurationError(
                "Invalid configuration type for Telegram notifier. Expected TelegramNotificationConfig."
            )

        # Get the config from the energy monitor config
        notifier_config: TelegramNotificationConfig = config

        if not notifier_config.bot_token:
            raise NotifierConfigurationError("Bot Token is required for Telegram notifier.")

        if not notifier_config.chat_id:
            raise NotifierConfigurationError("Chat ID is required for Telegram notifier.")

        return TelegramNotifier(
            bot_token=notifier_config.bot_token,
            chat_id=notifier_config.chat_id,
            logger=logger,
        )


# MarkdownV2 Special Characters That Need to Be Escaped
# See: https://core.telegram.org/bots/api#markdownv2-style
ESCAPE_CHARS = r"_*[]()~`>#+-=|{}.!"


def escape_markdown_v2(text: str) -> str:
    """Helper function to escape text for Telegram MarkdownV2 parsing."""
    # Use a regex to find and replace all special characters required
    return re.sub(f"([{re.escape(ESCAPE_CHARS)}])", r"\\\1", text)


class TelegramNotifier(NotificationPort):
    """Sends notifications to a specified Telegram chat using a bot."""

    def __init__(self, bot_token: str, chat_id: str, logger: Optional[LoggerPort]):
        self.logger = logger

        if not bot_token or not chat_id:
            raise ValueError("Telegram Bot Token and Chat ID are required.")

        self.token = bot_token
        self.chat_id = chat_id
        if self.logger:
            self.logger.info(f"Initializing TelegramNotifier for chat ID {chat_id}.")

        try:
            # Create the Bot instance.
            self.bot = telegram.Bot(token=self.token)

            if self.logger:
                self.logger.debug("Telegram Bot instance created.")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize Telegram Bot instance: {e}")
            raise ConnectionError(f"Could not initialize Telegram Bot: {e}") from e

    async def send_notification(self, title: str, message: str) -> bool:
        """Sends a formatted notification message to the configured Telegram chat."""
        if not self.bot:
            if self.logger:
                self.logger.error("Telegram Bot not initialized. Cannot send notification.")
            return False

        # Format the message using MarkdownV2 (make sure to escape!)
        escaped_title = escape_markdown_v2(title)
        escaped_message = escape_markdown_v2(message)
        formatted_message = f"*{escaped_title}*\n\n{escaped_message}"

        # Limit the message length (Telegram has a limit of 4096 characters)
        max_len = 4096
        if len(formatted_message) > max_len:
            if self.logger:
                self.logger.warning(f"Notification message exceeds Telegram limit ({max_len} chars). Truncating.")
            # Truncate preserving the base format
            truncated_message = escape_markdown_v2(
                message[: max_len - len(escaped_title) - 20]
            )  # Leave space for title and "..."
            formatted_message = f"*{escaped_title}*\n\n{truncated_message}\n\n\\.\\.\\. \\(truncated\\)"

        if self.logger:
            self.logger.debug(f"Sending notification to Telegram chat {self.chat_id}: Title='{title}'")
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=formatted_message,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            if self.logger:
                self.logger.info(f"Successfully sent notification to Telegram chat {self.chat_id}")
            return True
        except TelegramError as e:
            # Handle specific Telegram API errors
            if self.logger:
                self.logger.error(f"Telegram API error sending notification: {e}")
            if "chat not found" in str(e).lower():
                if self.logger:
                    self.logger.error(f"Invalid chat_id configured: {self.chat_id}")
            elif "bot was blocked by the user" in str(e).lower():
                if self.logger:
                    self.logger.warning(f"Bot was blocked by the user in chat {self.chat_id}.")
            # Other specific errors can be handled here
            return False
        except Exception as e:
            # Handle other errors (e.g. network)
            if self.logger:
                self.logger.error(f"Unexpected error sending notification via Telegram: {e}")
            return False
