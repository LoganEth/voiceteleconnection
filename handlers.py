import logging
from telegram import Update
from telegram.ext import ContextTypes
from voiceflow_client import VoiceflowClient

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self):
        self.voiceflow_client = VoiceflowClient()

    async def process_voiceflow_response(self, update: Update, traces: list):
        """Process and send Voiceflow response traces to the user"""
        for trace in traces:
            try:
                trace_type = trace.get('type')
                if trace_type in ['text', 'speak']:
                    await update.message.reply_text(trace['payload']['message'])
                elif trace_type == 'visual':
                    await update.message.reply_photo(trace['payload']['image'])
                elif trace_type == 'end':
                    await update.message.reply_text("Conversation ended. You can start a new one with /start")
            except Exception as e:
                logger.error(f"Error processing trace {trace_type}: {str(e)}")
                await update.message.reply_text("Sorry, I encountered an error processing the response.")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command"""
        try:
            user_id = str(update.effective_user.id)
            traces = await self.voiceflow_client.launch_conversation(user_id)
            await self.process_voiceflow_response(update, traces)
        except Exception as e:
            logger.error(f"Error in start command: {str(e)}")
            await update.message.reply_text("Sorry, I couldn't start the conversation. Please try again later.")

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        try:
            user_id = str(update.effective_user.id)
            message = update.message.text
            traces = await self.voiceflow_client.send_message(user_id, message)
            await self.process_voiceflow_response(update, traces)
        except Exception as e:
            logger.error(f"Error in message handler: {str(e)}")
            await update.message.reply_text("Sorry, I couldn't process your message. Please try again later.")
