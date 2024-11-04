import requests
import logging
from typing import Dict, Any, List
from config import VOICEFLOW_API_KEY, VOICEFLOW_BASE_URL, VOICEFLOW_VERSION

logger = logging.getLogger(__name__)

class VoiceflowClient:
    def __init__(self):
        self.base_url = VOICEFLOW_BASE_URL
        self.headers = {
            'Authorization': VOICEFLOW_API_KEY,
            'Content-Type': 'application/json',
            'versionID': VOICEFLOW_VERSION
        }

    async def _make_request(self, user_id: str, request: Dict[str, Any], version: str = None) -> List[Dict]:
        """
        Make a request to Voiceflow API with version fallback
        """
        headers = self.headers.copy()
        if version:
            headers['versionID'] = version

        try:
            url = f"{self.base_url}/state/user/{user_id}/interact"
            response = requests.post(url, headers=headers, json={'request': request})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if version == 'production' and str(e.response.status_code).startswith('4'):
                # If production version fails, try development version
                logger.warning("Production version not available, falling back to development version")
                headers['versionID'] = 'development'
                response = requests.post(url, headers=headers, json={'request': request})
                response.raise_for_status()
                return response.json()
            logger.error(f"Error interacting with Voiceflow API: {str(e)}")
            raise

    async def interact(self, user_id: str, request: Dict[str, Any]) -> List[Dict]:
        """
        Interact with the Voiceflow API using configured version
        """
        return await self._make_request(user_id, request, VOICEFLOW_VERSION)

    async def launch_conversation(self, user_id: str) -> List[Dict]:
        """Launch a new conversation"""
        return await self.interact(user_id, {'type': 'launch'})

    async def send_message(self, user_id: str, message: str) -> List[Dict]:
        """Send a text message to Voiceflow"""
        return await self.interact(user_id, {
            'type': 'text',
            'payload': message
        })

    async def handle_button_click(self, user_id: str, button_request: Dict[str, Any]) -> List[Dict]:
        """Handle button click interaction"""
        return await self.interact(user_id, button_request)
