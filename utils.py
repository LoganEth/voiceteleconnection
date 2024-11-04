import logging
from typing import Optional, Tuple
from telegram import Update

logger = logging.getLogger(__name__)

def get_user_identifier(update: Update) -> Optional[str]:
    """Extract user identifier from update"""
    try:
        return str(update.effective_user.id)
    except AttributeError:
        logger.error("Could not extract user ID from update")
        return None

def format_error_message(error: Exception) -> Tuple[str, str]:
    """Format error message for user display and logging"""
    error_type = type(error).__name__
    if isinstance(error, ConnectionError):
        return (
            "I'm having trouble connecting to my services. Please try again in a moment.",
            f"Connection error occurred: {str(error)}"
        )
    elif isinstance(error, TimeoutError):
        return (
            "The request took too long to process. Please try again.",
            f"Timeout error occurred: {str(error)}"
        )
    elif isinstance(error, requests.exceptions.RequestException):
        return (
            "There was an issue processing your request. Please try again later.",
            f"API request error: {str(error)}"
        )
    else:
        return (
            "I encountered an unexpected error. Please try again later.",
            f"Unexpected {error_type} occurred: {str(error)}"
        )

def validate_message(message: str) -> Tuple[bool, str]:
    """Validate user message"""
    if not message:
        return False, "Your message appears to be empty. Please try sending something!"
    if len(message) > 1000:  # Arbitrary limit
        return False, "Your message is too long. Please try sending a shorter message."
    return True, ""
