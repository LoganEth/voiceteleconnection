import logging
from typing import Set
from telegram.ext import ContextTypes
from telegram import Update
from utils import get_user_identifier

logger = logging.getLogger(__name__)

# Store admin user IDs
ADMIN_IDS: Set[str] = set()
# Store active user statistics
USER_STATS = {
    'total_users': set(),
    'total_messages': 0
}

class AdminHandler:
    @staticmethod
    def is_admin(user_id: str) -> bool:
        """Check if user is an admin"""
        return user_id in ADMIN_IDS

    @staticmethod
    async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add a new admin user"""
        user_id = get_user_identifier(update)
        if not user_id:
            return
            
        # First user to use this command becomes admin
        if not ADMIN_IDS:
            ADMIN_IDS.add(user_id)
            await update.message.reply_text("You are now the first admin!")
            return
            
        # Only existing admins can add new admins
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("You don't have permission to use this command.")
            return
            
        # Extract mentioned user
        if not context.args:
            await update.message.reply_text("Please provide a user ID to add as admin.")
            return
            
        new_admin_id = context.args[0]
        ADMIN_IDS.add(new_admin_id)
        await update.message.reply_text(f"User {new_admin_id} has been added as admin.")

    @staticmethod
    async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot statistics"""
        user_id = get_user_identifier(update)
        if not user_id or not AdminHandler.is_admin(user_id):
            await update.message.reply_text("You don't have permission to use this command.")
            return
            
        stats_message = (
            f"📊 Bot Statistics:\n"
            f"Total Users: {len(USER_STATS['total_users'])}\n"
            f"Total Messages: {USER_STATS['total_messages']}"
        )
        await update.message.reply_text(stats_message)

    @staticmethod
    async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Broadcast a message to all users"""
        user_id = get_user_identifier(update)
        if not user_id or not AdminHandler.is_admin(user_id):
            await update.message.reply_text("You don't have permission to use this command.")
            return
            
        if not context.args:
            await update.message.reply_text("Please provide a message to broadcast.")
            return
            
        broadcast_message = " ".join(context.args)
        success_count = 0
        
        for user_id in USER_STATS['total_users']:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 Broadcast: {broadcast_message}"
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send broadcast to user {user_id}: {str(e)}")
                
        await update.message.reply_text(
            f"Broadcast sent successfully to {success_count}/{len(USER_STATS['total_users'])} users."
        )

    @staticmethod
    async def help_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin command help"""
        user_id = get_user_identifier(update)
        if not user_id or not AdminHandler.is_admin(user_id):
            await update.message.reply_text("You don't have permission to use this command.")
            return
            
        help_text = (
            "🔑 Admin Commands:\n\n"
            "/add_admin <user_id> - Add a new admin\n"
            "/stats - Show bot statistics\n"
            "/broadcast <message> - Send message to all users\n"
            "/help_admin - Show this help message"
        )
        await update.message.reply_text(help_text)

    @staticmethod
    def update_stats(user_id: str):
        """Update user statistics"""
        USER_STATS['total_users'].add(user_id)
        USER_STATS['total_messages'] += 1
