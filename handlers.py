import logging
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from voiceflow_client import VoiceflowClient
from admin_handlers import AdminHandler
from utils import get_user_identifier, format_error_message, validate_message

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self):
        self.voiceflow_client = VoiceflowClient()
        self.admin_handler = AdminHandler()

    async def show_typing(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE, duration: float = 1.0):
        """Show typing indicator for specified duration"""
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            if duration > 0:
                await asyncio.sleep(duration)
        except Exception as e:
            logger.error(f"Error showing typing indicator: {str(e)}")

    async def calculate_typing_duration(self, message: str) -> float:
        """Calculate typing duration based on message length"""
        if not message:
            return 1.0
        # Average reading speed is about 200 words per minute
        # So we'll show typing for about 1 second per 5 words
        words = len(message.split())
        return min(max(words / 5, 1.0), 5.0)  # Min 1 second, max 5 seconds

    async def process_voiceflow_response(self, update: Update, traces: list, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False):
        """Process and send Voiceflow response traces to the user"""
        if not traces:
            message = "I didn't receive a response. Let's try starting over with /start"
            msg_obj = update.callback_query.message if is_callback else update.message
            if msg_obj:
                await msg_obj.reply_text(message)
            return

        # Get chat ID and message object
        msg_obj = update.callback_query.message if is_callback else update.message
        if not msg_obj:
            logger.error("No valid message object found")
            return
            
        chat_id = msg_obj.chat_id

        for trace in traces:
            try:
                trace_type = trace.get('type')
                if not trace_type:
                    continue

                if trace_type in ['text', 'speak']:
                    message = trace.get('payload', {}).get('message')
                    if message:
                        # Show typing indicator before sending text
                        typing_duration = await self.calculate_typing_duration(message)
                        await self.show_typing(chat_id, context, typing_duration)
                        await msg_obj.reply_text(message)
                elif trace_type == 'visual':
                    image_url = trace.get('payload', {}).get('image')
                    if image_url:
                        # Show upload photo action for images
                        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
                        await asyncio.sleep(2.0)  # Give time for "uploading photo" indicator
                        await msg_obj.reply_photo(image_url)
                elif trace_type == 'choice':
                    buttons = trace.get('payload', {}).get('buttons', [])
                    if buttons:
                        # Show typing before sending button options
                        await self.show_typing(chat_id, context, 1.0)
                        keyboard = []
                        for button in buttons:
                            callback_data = f"button_{button['request']['type']}_{button['name']}"
                            keyboard.append([InlineKeyboardButton(button['name'], callback_data=callback_data)])
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await msg_obj.reply_text("Please choose an option:", reply_markup=reply_markup)
                elif trace_type == 'end':
                    await self.show_typing(chat_id, context, 1.0)
                    await msg_obj.reply_text("Conversation ended. You can start a new one with /start")
            except Exception as e:
                logger.error(f"Error processing trace {trace_type}: {str(e)}")
                user_msg, log_msg = format_error_message(e)
                logger.error(log_msg)
                if msg_obj:
                    await msg_obj.reply_text(user_msg)

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callback queries"""
        try:
            query = update.callback_query
            if not query:
                logger.error("No callback query found")
                return
                
            await query.answer()  # Answer the callback query to remove the loading state

            # Extract button info from callback data
            _, button_type, button_label = query.data.split('_', 2)
            user_id = str(query.from_user.id)

            # Show typing indicator while processing
            if query.message:
                await self.show_typing(query.message.chat_id, context, 1.0)

            # Create the appropriate request based on button type
            if button_type == 'intent':
                request = {
                    'type': 'intent',
                    'payload': {
                        'intent': {
                            'name': button_label.lower().replace(' ', '_')
                        },
                        'query': button_label,
                        'entities': []
                    }
                }
            else:  # Path ID or other types
                request = {
                    'type': button_type,
                    'payload': {
                        'label': button_label
                    }
                }

            # Send the request to Voiceflow
            traces = await self.voiceflow_client.handle_button_click(user_id, request)
            
            # Process the response with is_callback=True
            await self.process_voiceflow_response(update, traces, context, is_callback=True)

        except Exception as e:
            user_msg, log_msg = format_error_message(e)
            logger.error(f"Error in button callback: {log_msg}")
            if query and query.message:
                await query.message.reply_text(user_msg)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command"""
        try:
            user_id = get_user_identifier(update)
            if not user_id or not update.message:
                await update.message.reply_text("I couldn't identify you. Please try again later.")
                return

            # Update stats for new user
            AdminHandler.update_stats(user_id)
            
            # Show typing indicator while initializing
            await self.show_typing(update.message.chat_id, context, 2.0)
            
            try:
                traces = await self.voiceflow_client.launch_conversation(user_id)
                await self.process_voiceflow_response(update, traces, context)
            except requests.exceptions.RequestException as e:
                user_msg, log_msg = format_error_message(e)
                logger.error(log_msg)
                await update.message.reply_text(user_msg)
                
        except Exception as e:
            user_msg, log_msg = format_error_message(e)
            logger.error(f"Error in start command: {log_msg}")
            if update.message:
                await update.message.reply_text(user_msg)

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /clear command to reset conversation history"""
        try:
            user_id = get_user_identifier(update)
            if not user_id or not update.message:
                await update.message.reply_text("I couldn't identify you. Please try again later.")
                return

            # Show typing indicator while clearing
            await self.show_typing(update.message.chat_id, context, 1.0)

            success = await self.voiceflow_client.clear_state(user_id)
            if success:
                await update.message.reply_text("Conversation history cleared. You can start a new conversation with /start")
            else:
                await update.message.reply_text("Sorry, I couldn't clear the conversation history. Please try again later.")

        except Exception as e:
            user_msg, log_msg = format_error_message(e)
            logger.error(f"Error in clear command: {log_msg}")
            if update.message:
                await update.message.reply_text(user_msg)

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        try:
            user_id = get_user_identifier(update)
            if not user_id or not update.message:
                await update.message.reply_text("I couldn't identify you. Please try again later.")
                return

            # Update stats for message
            AdminHandler.update_stats(user_id)
            
            message = update.message.text
            if not message:
                await update.message.reply_text("Your message appears to be empty. Please try sending something!")
                return
                
            # Validate message
            is_valid, error_message = validate_message(message)
            if not is_valid:
                await update.message.reply_text(error_message)
                return

            # Show initial typing indicator
            await self.show_typing(update.message.chat_id, context, 1.0)

            try:
                traces = await self.voiceflow_client.send_message(user_id, message)
                await self.process_voiceflow_response(update, traces, context)
            except requests.exceptions.RequestException as e:
                user_msg, log_msg = format_error_message(e)
                logger.error(log_msg)
                await update.message.reply_text(user_msg)
                
        except Exception as e:
            user_msg, log_msg = format_error_message(e)
            logger.error(f"Error in message handler: {log_msg}")
            if update.message:
                await update.message.reply_text(user_msg)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command"""
        if not update.message:
            return
            
        # Show typing indicator before sending help text
        await self.show_typing(update.message.chat_id, context, 1.0)
        
        help_text = (
            "🤖 Bot Commands:\n\n"
            "/start - Start or restart a conversation\n"
            "/clear - Clear conversation history\n"
            "/help - Show this help message\n"
        )
        await update.message.reply_text(help_text)
