import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Bot Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
VOICEFLOW_API_KEY = os.getenv('VOICEFLOW_API_KEY')
VOICEFLOW_BASE_URL = 'https://general-runtime.voiceflow.com'
VOICEFLOW_VERSION = os.getenv('VOICEFLOW_VERSION_ID', 'production')  # Default to production version

# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL)
)
logger = logging.getLogger(__name__)

# Validate configuration
if not TELEGRAM_TOKEN:
    logger.error("Telegram token not found in environment variables")
    raise ValueError("TELEGRAM_TOKEN environment variable is required")

if not VOICEFLOW_API_KEY:
    logger.error("Voiceflow API key not found in environment variables")
    raise ValueError("VOICEFLOW_API_KEY environment variable is required")
