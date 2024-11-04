import logging
import requests
from telegram import Update
from telegram.ext import ContextTypes
from voiceflow_client import VoiceflowClient
from admin_handlers import AdminHandler
from utils import get_user_identifier, format_error_message, validate_message

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self):
        self.voiceflow_client = VoiceflowClient()
        self.admin_handler = AdminHandler()

    async def process_voiceflow_response(self, update: Update, traces: list):
        """Process and send Voiceflow response traces to the user"""
        if not traces:
            await update.message.reply_text("I didn't receive a response. Let's try starting over with /start")
            return

        for trace in traces:
            try:
                trace_type = trace.get('type')
                if not trace_type:
                    continue

                if trace_type in ['text', 'speak']:
                    message = trace.get('payload', {}).get('message')
                    if message:
                        await update.message.reply_text(message)
                elif trace_type == 'visual':
                    image_url = trace.get('payload', {}).get('image')
                    if image_url:
                        await update.message.reply_photo(image_url)
                elif trace_type == 'end':
                    await update.message.reply_text("Conversation ended. You can start a new one with /start")
            except Exception as e:
                logger.error(f"Error processing trace {trace_type}: {str(e)}")
                user_msg, log_msg = format_error_message(e)
                logger.error(log_msg)
                await update.message.reply_text(user_msg)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command"""
        try:
            user_id = get_user_identifier(update)
            if not user_id:
                await update.message.reply_text("I couldn't identify you. Please try again later.")
                return

            # Update stats for new user
            AdminHandler.update_stats(user_id)
            
            try:
                traces = await self.voiceflow_client.launch_conversation(user_id)
                await self.process_voiceflow_response(update, traces)
            except requests.exceptions.RequestException as e:
                user_msg, log_msg = format_error_message(e)
                logger.error(log_msg)
                await update.message.reply_text(user_msg)
                
        except Exception as e:
            user_msg, log_msg = format_error_message(e)
            logger.error(f"Error in start command: {log_msg}")
            await update.message.reply_text(user_msg)

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        try:
            user_id = get_user_identifier(update)
            if not user_id:
                await update.message.reply_text("I couldn't identify you. Please try again later.")
                return

            # Update stats for message
            AdminHandler.update_stats(user_id)
            
            message = update.message.text
            # Validate message
            is_valid, error_message = validate_message(message)
            if not is_valid:
                await update.message.reply_text(error_message)
                return

            try:
                traces = await self.voiceflow_client.send_message(user_id, message)
                await self.process_voiceflow_response(update, traces)
            except requests.exceptions.RequestException as e:
                user_msg, log_msg = format_error_message(e)
                logger.error(log_msg)
                await update.message.reply_text(user_msg)
                
        except Exception as e:
            user_msg, log_msg = format_error_message(e)
            logger.error(f"Error in message handler: {log_msg}")
            await update.message.reply_text(user_msg)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command"""
        help_text = (
            "🤖 Bot Commands:\n\n"
            "/start - Start or restart a conversation\n"
            "/help - Show this help message\n"
        )
        await update.message.reply_text(help_text)
