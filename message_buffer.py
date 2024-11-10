import asyncio
import random
from typing import Any, Callable, Coroutine, Optional, List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class MessageBuffer:
    def __init__(self, min_delay: float = 0.5, max_delay: float = 2.0, chars_per_second: float = 15, 
                 collection_timeout: float = 1.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.chars_per_second = chars_per_second
        self.collection_timeout = collection_timeout
        self.message_queue: List[Tuple[Callable[..., Coroutine[Any, Any, None]], tuple, dict, bool]] = []
        self.collection_buffer: List[Dict[str, Any]] = []
        self.collection_timer: Optional[asyncio.Task] = None
        self.user_message_buffer: Dict[str, List[str]] = {}
        self.user_message_timers: Dict[str, asyncio.Task] = {}
        
    def calculate_typing_duration(self, message: str) -> float:
        """Calculate typing duration based on message length"""
        if not message or not isinstance(message, str):
            return self.min_delay
        return max(self.min_delay, min(len(message) / self.chars_per_second, self.max_delay * 2))
        
    async def add_message(self, send_func: Callable[..., Coroutine[Any, Any, None]], *args, 
                         is_user_input: bool = False, user_id: Optional[str] = None, **kwargs):
        """Add a message to the collection buffer"""
        message_data = {
            'send_func': send_func,
            'args': args,
            'kwargs': kwargs,
            'is_user_input': is_user_input,
            'user_id': user_id
        }
        
        # If it's a user message and has user_id, add to user message buffer
        if is_user_input and user_id and isinstance(args[0], str):
            if user_id not in self.user_message_buffer:
                self.user_message_buffer[user_id] = []
            self.user_message_buffer[user_id].append(args[0])
            
            # Cancel existing timer if any
            if user_id in self.user_message_timers:
                self.user_message_timers[user_id].cancel()
            
            # Create new timer for this user
            self.user_message_timers[user_id] = asyncio.create_task(
                self.process_user_messages(user_id)
            )
            return

        # Add non-user messages to collection buffer
        self.collection_buffer.append(message_data)
        
        # Start or reset collection timer
        if self.collection_timer:
            self.collection_timer.cancel()
        
        self.collection_timer = asyncio.create_task(self.process_collection())

    async def process_user_messages(self, user_id: str):
        """Process collected user messages after timeout"""
        try:
            await asyncio.sleep(self.collection_timeout)
            messages = self.user_message_buffer.pop(user_id, [])
            if messages:
                # Combine messages
                combined_message = " ".join(messages)
                # Add to regular message queue for processing
                self.message_queue.append((
                    self.dummy_send_func,
                    (combined_message,),
                    {'user_id': user_id},
                    True
                ))
                await self.process_queue()
        except Exception as e:
            logger.error(f"Error processing user messages: {str(e)}")
        finally:
            if user_id in self.user_message_timers:
                del self.user_message_timers[user_id]

    async def dummy_send_func(self, message: str, user_id: str):
        """Dummy function for combined messages"""
        # This will be replaced by actual send function in handlers
        pass
        
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
            
        # Process any remaining user message buffers
        for user_id in list(self.user_message_timers.keys()):
            if user_id in self.user_message_timers:
                self.user_message_timers[user_id].cancel()
            await self.process_user_messages(user_id)
            
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

    def get_combined_messages(self, user_id: str) -> List[str]:
        """Get combined messages for a user"""
        return self.user_message_buffer.get(user_id, [])
