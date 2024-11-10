import logging
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from voiceflow_client import VoiceflowClient
from admin_handlers import AdminHandler
from utils import get_user_identifier, format_error_message, validate_message
from message_buffer import MessageBuffer

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self):
        self.voiceflow_client = VoiceflowClient()
        self.admin_handler = AdminHandler()
        self.message_buffer = MessageBuffer()
        self.processing_lock = {}  # Lock per user to prevent concurrent processing

    async def process_voiceflow_response(self, update: Update, traces: list, is_callback: bool = False):
        """Process and send Voiceflow response traces to the user"""
        if not traces:
            message = "I didn't receive a response. Let's try starting over with /start"
            if is_callback:
                await update.callback_query.message.reply_text(message)
            else:
                await update.message.reply_text(message)
            return

        # Get the appropriate message object based on context
        msg_obj = update.callback_query.message if is_callback else update.message

        for trace in traces:
            try:
                trace_type = trace.get('type')
                if not trace_type:
                    continue

                if trace_type in ['text', 'speak']:
                    message = trace.get('payload', {}).get('message')
                    if message:
                        await self.message_buffer.add_message(msg_obj.reply_text, message, is_user_input=False)
                elif trace_type == 'visual':
                    image_url = trace.get('payload', {}).get('image')
                    if image_url:
                        await self.message_buffer.add_message(msg_obj.reply_photo, image_url, is_user_input=False)
                elif trace_type == 'choice':
                    buttons = trace.get('payload', {}).get('buttons', [])
                    if buttons:
                        keyboard = []
                        for button in buttons:
                            callback_data = f"button_{button['request']['type']}_{button['name']}"
                            keyboard.append([InlineKeyboardButton(button['name'], callback_data=callback_data)])
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await self.message_buffer.add_message(
                            msg_obj.reply_text,
                            "Please choose an option:",
                            reply_markup=reply_markup,
                            is_user_input=False
                        )
                elif trace_type == 'end':
                    await self.message_buffer.add_message(
                        msg_obj.reply_text,
                        "Conversation ended. You can start a new one with /start",
                        is_user_input=False
                    )
            except Exception as e:
                logger.error(f"Error processing trace {trace_type}: {str(e)}")
                user_msg, log_msg = format_error_message(e)
                logger.error(log_msg)
                await msg_obj.reply_text(user_msg)

        # Process all buffered messages
        await self.message_buffer.flush()

    async def acquire_user_lock(self, user_id: str) -> bool:
        """Acquire lock for user processing"""
        if user_id not in self.processing_lock:
            self.processing_lock[user_id] = asyncio.Lock()
        
        try:
            await asyncio.wait_for(self.processing_lock[user_id].acquire(), timeout=1.0)
            return True
        except asyncio.TimeoutError:
            return False

    def release_user_lock(self, user_id: str):
        """Release lock for user processing"""
        if user_id in self.processing_lock and self.processing_lock[user_id].locked():
            self.processing_lock[user_id].release()

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callback queries"""
        try:
            query = update.callback_query
            await query.answer()  # Answer the callback query to remove the loading state

            # Extract button info from callback data
            _, button_type, button_label = query.data.split('_', 2)
            user_id = str(query.from_user.id)

            # Try to acquire lock for this user
            if not await self.acquire_user_lock(user_id):
                await query.message.reply_text("Please wait for your previous request to complete.")
                return

            try:
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

                # Add typing indicator to buffer
                await self.message_buffer.add_message(
                    context.bot.send_chat_action,
                    chat_id=query.message.chat_id,
                    action="typing",
                    is_user_input=True
                )
                await self.message_buffer.flush()

                # Send the request to Voiceflow
                traces = await self.voiceflow_client.handle_button_click(user_id, request)
                
                # Process the response with is_callback=True
                await self.process_voiceflow_response(update, traces, is_callback=True)

            finally:
                self.release_user_lock(user_id)

        except Exception as e:
            user_msg, log_msg = format_error_message(e)
            logger.error(f"Error in button callback: {log_msg}")
            await query.message.reply_text(user_msg)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command"""
        try:
            user_id = get_user_identifier(update)
            if not user_id:
                await update.message.reply_text("I couldn't identify you. Please try again later.")
                return

            # Try to acquire lock for this user
            if not await self.acquire_user_lock(user_id):
                await update.message.reply_text("Please wait for your previous request to complete.")
                return

            try:
                # Update stats for new user
                AdminHandler.update_stats(user_id)
                
                # Add typing indicator to buffer
                await self.message_buffer.add_message(
                    context.bot.send_chat_action,
                    chat_id=update.message.chat_id,
                    action="typing",
                    is_user_input=True
                )
                await self.message_buffer.flush()

                traces = await self.voiceflow_client.launch_conversation(user_id)
                await self.process_voiceflow_response(update, traces)

            finally:
                self.release_user_lock(user_id)
                
        except Exception as e:
            user_msg, log_msg = format_error_message(e)
            logger.error(f"Error in start command: {log_msg}")
            await update.message.reply_text(user_msg)

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /clear command to reset conversation history"""
        try:
            user_id = get_user_identifier(update)
            if not user_id:
                await update.message.reply_text("I couldn't identify you. Please try again later.")
                return

            # Try to acquire lock for this user
            if not await self.acquire_user_lock(user_id):
                await update.message.reply_text("Please wait for your previous request to complete.")
                return

            try:
                success = await self.voiceflow_client.clear_state(user_id)
                if success:
                    await self.message_buffer.add_message(
                        update.message.reply_text,
                        "Conversation history cleared. You can start a new conversation with /start",
                        is_user_input=False
                    )
                    await self.message_buffer.flush()
                else:
                    await update.message.reply_text("Sorry, I couldn't clear the conversation history. Please try again later.")

            finally:
                self.release_user_lock(user_id)

        except Exception as e:
            user_msg, log_msg = format_error_message(e)
            logger.error(f"Error in clear command: {log_msg}")
            await update.message.reply_text(user_msg)

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        try:
            user_id = get_user_identifier(update)
            if not user_id:
                await update.message.reply_text("I couldn't identify you. Please try again later.")
                return

            # Try to acquire lock for this user
            if not await self.acquire_user_lock(user_id):
                await update.message.reply_text("Please wait for your previous request to complete.")
                return

            try:
                # Update stats for message
                AdminHandler.update_stats(user_id)
                
                message = update.message.text
                # Validate message
                is_valid, error_message = validate_message(message)
                if not is_valid:
                    await update.message.reply_text(error_message)
                    return

                # Add typing indicator to buffer
                await self.message_buffer.add_message(
                    context.bot.send_chat_action,
                    chat_id=update.message.chat_id,
                    action="typing",
                    is_user_input=True
                )
                await self.message_buffer.flush()

                traces = await self.voiceflow_client.send_message(user_id, message)
                await self.process_voiceflow_response(update, traces)

            finally:
                self.release_user_lock(user_id)
                
        except Exception as e:
            user_msg, log_msg = format_error_message(e)
            logger.error(f"Error in message handler: {log_msg}")
            await update.message.reply_text(user_msg)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command"""
        help_text = (
            "🤖 Bot Commands:\n\n"
            "/start - Start or restart a conversation\n"
            "/clear - Clear conversation history\n"
            "/help - Show this help message\n"
        )
        await self.message_buffer.add_message(update.message.reply_text, help_text, is_user_input=False)
        await self.message_buffer.flush()
