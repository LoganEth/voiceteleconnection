import logging
from typing import Optional
from telegram import Update

logger = logging.getLogger(__name__)

def get_user_identifier(update: Update) -> Optional[str]:
    """Extract user identifier from update"""
    try:
        return str(update.effective_user.id)
    except AttributeError:
        logger.error("Could not extract user ID from update")
        return None

def format_error_message(error: Exception) -> str:
    """Format error message for user display"""
    return "I encountered an error. Please try again later."
