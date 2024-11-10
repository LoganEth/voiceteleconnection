import asyncio
import random
from typing import Any, Callable, Coroutine, Optional
import logging

logger = logging.getLogger(__name__)

class MessageBuffer:
    def __init__(self, min_delay: float = 0.5, max_delay: float = 2.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.message_queue = []
        
    async def add_message(self, send_func: Callable[..., Coroutine[Any, Any, None]], *args, **kwargs):
        """Add a message to the buffer"""
        self.message_queue.append((send_func, args, kwargs))
        
    async def process_queue(self):
        """Process all messages in the queue with random delays"""
        while self.message_queue:
            send_func, args, kwargs = self.message_queue.pop(0)
            try:
                # Random delay before sending
                delay = random.uniform(self.min_delay, self.max_delay)
                await asyncio.sleep(delay)
                
                # Send the message
                await send_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error processing buffered message: {str(e)}")
                
    async def flush(self):
        """Process all remaining messages in the queue"""
        await self.process_queue()
