import asyncio
import random
from typing import Any, Callable, Coroutine, Optional, List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class MessageBuffer:
    def __init__(self, min_delay: float = 0.5, max_delay: float = 2.0, chars_per_second: float = 15):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.chars_per_second = chars_per_second
        self.message_queue: List[Tuple[Callable[..., Coroutine[Any, Any, None]], tuple, dict, bool]] = []
        self.collection_buffer: List[Dict[str, Any]] = []
        self.collection_timer: Optional[asyncio.Task] = None
        
    def calculate_typing_duration(self, message: str) -> float:
        """Calculate typing duration based on message length"""
        if not message or not isinstance(message, str):
            return self.min_delay
        return max(self.min_delay, min(len(message) / self.chars_per_second, self.max_delay * 2))
        
    async def add_message(self, send_func: Callable[..., Coroutine[Any, Any, None]], *args, is_user_input: bool = False, **kwargs):
        """Add a message to the collection buffer"""
        message_data = {
            'send_func': send_func,
            'args': args,
            'kwargs': kwargs,
            'is_user_input': is_user_input
        }
        
        # Add message to collection buffer
        self.collection_buffer.append(message_data)
        
        # Start or reset collection timer
        if self.collection_timer:
            self.collection_timer.cancel()
        
        self.collection_timer = asyncio.create_task(self.process_collection())
        
    async def process_collection(self):
        """Process collected messages after a short delay"""
        try:
            # Wait for a short time to collect related messages
            await asyncio.sleep(0.1)
            
            # Move messages from collection buffer to queue
            while self.collection_buffer:
                message_data = self.collection_buffer.pop(0)
                self.message_queue.append((
                    message_data['send_func'],
                    message_data['args'],
                    message_data['kwargs'],
                    message_data['is_user_input']
                ))
            
            # Process the queue
            await self.process_queue()
            
        except Exception as e:
            logger.error(f"Error processing message collection: {str(e)}")
        finally:
            self.collection_timer = None
            
    async def process_queue(self):
        """Process all messages in the queue with smart delays"""
        prev_message_time = 0
        
        while self.message_queue:
            send_func, args, kwargs, is_user_input = self.message_queue.pop(0)
            try:
                current_time = asyncio.get_event_loop().time()
                
                # Calculate delay based on message type and content
                delay = 0
                if is_user_input:
                    # For user input, use random delay
                    delay = random.uniform(self.min_delay, self.max_delay)
                elif args and isinstance(args[0], str):
                    # For text messages, calculate typing duration
                    delay = self.calculate_typing_duration(args[0])
                    # Ensure minimum time between messages
                    if current_time - prev_message_time < self.min_delay:
                        delay += self.min_delay
                
                if delay > 0:
                    await asyncio.sleep(delay)
                
                # Send the message
                await send_func(*args, **kwargs)
                prev_message_time = asyncio.get_event_loop().time()
                
            except Exception as e:
                logger.error(f"Error processing buffered message: {str(e)}")
                
    async def flush(self):
        """Process all remaining messages in the buffers"""
        # Cancel any pending collection timer
        if self.collection_timer:
            self.collection_timer.cancel()
            self.collection_timer = None
            
        # Move any collected messages to queue
        while self.collection_buffer:
            message_data = self.collection_buffer.pop(0)
            self.message_queue.append((
                message_data['send_func'],
                message_data['args'],
                message_data['kwargs'],
                message_data['is_user_input']
            ))
            
        # Process all queued messages
        await self.process_queue()
