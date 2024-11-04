import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler as TelegramMessageHandler
from telegram.ext import filters
from config import TELEGRAM_TOKEN
from handlers import MessageHandler

logger = logging.getLogger(__name__)

def main():
    """Initialize and start the bot"""
    try:
        # Create application
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Initialize handlers
        message_handler = MessageHandler()
        
        # Add handlers
        application.add_handler(CommandHandler("start", message_handler.start_command))
        application.add_handler(TelegramMessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler.message_handler
        ))
        
        # Start the bot
        logger.info("Starting bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
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
