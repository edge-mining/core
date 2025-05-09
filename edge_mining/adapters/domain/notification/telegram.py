"""Telegram adapter (Implementation of Port) that uses telegram as notificator sender for Edge Mining Application"""

import re
import telegram

from telegram.constants import ParseMode
from telegram.error import TelegramError

from edge_mining.domain.notification.ports import NotificationPort
from edge_mining.adapters.infrastructure.logging.terminal_logging import TerminalLogger

# Caratteri speciali di MarkdownV2 che devono essere escapati
# Vedi: https://core.telegram.org/bots/api#markdownv2-style
ESCAPE_CHARS = r'_*[]()~`>#+-=|{}.!'

def escape_markdown_v2(text: str) -> str:
    """Helper function to escape text for Telegram MarkdownV2 parsing."""
    # Usa una regex per trovare e sostituire tutti i caratteri speciali richiesti
    return re.sub(f'([{re.escape(ESCAPE_CHARS)}])', r'\\\1', text)

class TelegramNotifier(NotificationPort):
    """Sends notifications to a specified Telegram chat using a bot."""

    def __init__(self, bot_token: str, chat_id: str, logger: TerminalLogger):
        self.logger = logger

        if not bot_token or not chat_id:
            raise ValueError("Telegram Bot Token and Chat ID are required.")
        
        self.token = bot_token
        self.chat_id = chat_id
        self.logger.info(f"Initializing TelegramNotifier for chat ID {chat_id}")
        
        try:
            # Create the Bot instance.
            self.bot = telegram.Bot(token=self.token)

            self.logger.debug("Telegram Bot instance created.")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram Bot instance: {e}")
            raise ConnectionError(f"Could not initialize Telegram Bot: {e}") from e

    async def send_notification(self, title: str, message: str) -> bool:
        """Sends a formatted notification message to the configured Telegram chat."""
        if not self.bot:
            self.logger.error("Telegram Bot not initialized. Cannot send notification.")
            return False

        # Formatta il messaggio usando MarkdownV2 (assicurati di fare l'escaping!)
        escaped_title = escape_markdown_v2(title)
        escaped_message = escape_markdown_v2(message)
        formatted_message = f"*{escaped_title}*\n\n{escaped_message}"

        # Limita la lunghezza del messaggio (Telegram ha un limite di 4096 caratteri)
        max_len = 4096
        if len(formatted_message) > max_len:
            self.logger.warning(f"Notification message exceeds Telegram limit ({max_len} chars). Truncating.")
            # Tronca preservando il formato di base
            truncated_message = escape_markdown_v2(message[:max_len - len(escaped_title) - 20]) # Lascia spazio per titolo e "..."
            formatted_message = f"*{escaped_title}*\n\n{truncated_message}\n\n\\.\\.\\. \\(truncated\\)"


        self.logger.debug(f"Sending notification to Telegram chat {self.chat_id}: Title='{title}'")
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=formatted_message,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            self.logger.info(f"Successfully sent notification to Telegram chat {self.chat_id}")
            return True
        except TelegramError as e:
            # Gestisce specifici errori API di Telegram
            self.logger.error(f"Telegram API error sending notification: {e}")
            if "chat not found" in str(e).lower():
                self.logger.error(f"Invalid chat_id configured: {self.chat_id}")
            elif "bot was blocked by the user" in str(e).lower():
                 self.logger.warning(f"Bot was blocked by the user in chat {self.chat_id}.")
            # Altri errori specifici possono essere gestiti qui
            return False
        except Exception as e:
            # Gestisce altri errori (es. rete)
            self.logger.error(f"Unexpected error sending notification via Telegram: {e}")
            return False