import logging
from telegram.ext import Updater, CommandHandler, MessageHandler as TelegramMessageHandler, Filters
from config import TELEGRAM_TOKEN
from handlers import MessageHandler
from admin_handlers import AdminHandler

logger = logging.getLogger(__name__)

def main():
    """Initialize and start the bot"""
    try:
        # Create updater and dispatcher
        updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # Initialize handlers
        message_handler = MessageHandler()
        admin_handler = AdminHandler()
        
        # Add regular handlers
        dispatcher.add_handler(CommandHandler("start", message_handler.start_command))
        dispatcher.add_handler(CommandHandler("help", message_handler.help_command))
        
        # Add admin handlers
        dispatcher.add_handler(CommandHandler("add_admin", admin_handler.add_admin_command))
        dispatcher.add_handler(CommandHandler("stats", admin_handler.stats_command))
        dispatcher.add_handler(CommandHandler("broadcast", admin_handler.broadcast_command))
        dispatcher.add_handler(CommandHandler("help_admin", admin_handler.help_admin_command))
        
        # Add message handler (should be last)
        dispatcher.add_handler(TelegramMessageHandler(
            Filters.text & ~Filters.command,
            message_handler.message_handler
        ))
        
        # Start the bot
        logger.info("Starting bot...")
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
