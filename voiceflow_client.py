import requests
import logging
from typing import Dict, Any, List
from config import VOICEFLOW_API_KEY, VOICEFLOW_BASE_URL

logger = logging.getLogger(__name__)

class VoiceflowClient:
    def __init__(self):
        self.base_url = VOICEFLOW_BASE_URL
        self.headers = {
            'Authorization': VOICEFLOW_API_KEY,
            'Content-Type': 'application/json'
        }

    async def interact(self, user_id: str, request: Dict[str, Any]) -> List[Dict]:
        """
        Interact with the Voiceflow API
        
        Args:
            user_id: The unique identifier for the user
            request: The request payload to send to Voiceflow
            
        Returns:
            List of response traces from Voiceflow
        """
        try:
            url = f"{self.base_url}/state/user/{user_id}/interact"
            response = requests.post(url, headers=self.headers, json={'request': request})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error interacting with Voiceflow API: {str(e)}")
            raise

    async def launch_conversation(self, user_id: str) -> List[Dict]:
        """Launch a new conversation"""
        return await self.interact(user_id, {'type': 'launch'})

    async def send_message(self, user_id: str, message: str) -> List[Dict]:
        """Send a text message to Voiceflow"""
        return await self.interact(user_id, {
            'type': 'text',
            'payload': message
        })
