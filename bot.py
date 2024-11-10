import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler as TelegramMessageHandler, CallbackQueryHandler
from telegram.ext import filters
from config import TELEGRAM_TOKEN
from handlers import MessageHandler
from admin_handlers import AdminHandler

logger = logging.getLogger(__name__)

def main():
    """Initialize and start the bot"""
    try:
        # Create application
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Initialize handlers
        message_handler = MessageHandler()
        admin_handler = AdminHandler()
        
        # Add regular handlers
        application.add_handler(CommandHandler("start", message_handler.start_command))
        application.add_handler(CommandHandler("help", message_handler.help_command))
        application.add_handler(CommandHandler("clear", message_handler.clear_command))
        
        # Add admin handlers
        application.add_handler(CommandHandler("add_admin", admin_handler.add_admin_command))
        application.add_handler(CommandHandler("stats", admin_handler.stats_command))
        application.add_handler(CommandHandler("broadcast", admin_handler.broadcast_command))
        application.add_handler(CommandHandler("help_admin", admin_handler.help_admin_command))
        
        # Add callback query handler for buttons
        application.add_handler(CallbackQueryHandler(message_handler.button_callback))
        
        # Add message handler (should be last)
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
