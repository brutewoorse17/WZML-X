#!/usr/bin/env python3
"""
Auto-Download Module for WZML-X Bot

This module handles automatic detection and downloading of supported URLs
from user messages without requiring explicit commands.
"""

import asyncio
from pyrogram import filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from bot import bot, LOGGER, user_data, config_dict
from bot.helper.ext_utils.url_auto_detector import (
    url_detector,
    detect_urls_in_message,
    should_auto_download,
    get_url_info
)
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, editMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import new_task

class AutoDownloadManager:
    """Manages automatic URL detection and download processes"""
    
    def __init__(self):
        self.processing_urls = set()  # Track URLs being processed
        self.user_confirmations = {}  # Track pending user confirmations
        
    async def process_message_urls(self, message: Message):
        """Process URLs found in a message"""
        try:
            # Extract URLs from message
            urls = detect_urls_in_message(message.text or message.caption or "")
            
            if not urls:
                return
            
            user_id = message.from_user.id
            
            # Filter URLs that should be auto-downloaded
            downloadable_urls = []
            for url, metadata in urls:
                if url not in self.processing_urls:
                    if should_auto_download(url, user_id):
                        downloadable_urls.append((url, metadata))
                    elif self.should_prompt_user(url, metadata, user_id):
                        await self.prompt_user_for_download(message, url, metadata)
            
            if not downloadable_urls:
                return
            
            # Sort by priority
            downloadable_urls.sort(key=lambda x: url_detector.get_download_priority(x[0]), reverse=True)
            
            # Process downloads
            for url, metadata in downloadable_urls:
                await self.initiate_auto_download(message, url, metadata)
                
        except Exception as e:
            LOGGER.error(f"Error processing message URLs: {str(e)}")
    
    def should_prompt_user(self, url: str, metadata: Dict, user_id: int) -> bool:
        """Check if user should be prompted for download confirmation"""
        if user_id not in user_data:
            return False
            
        user_prefs = user_data[user_id].get('auto_download', {})
        
        # Check if prompting is enabled
        if not user_prefs.get('prompt_enabled', True):
            return False
        
        # Don't prompt for unsafe or unknown types
        safe_types = ['gdrive', 'mega', 'youtube', 'torrent_file', 'magnet']
        if metadata.get('estimated_type') not in safe_types:
            return False
        
        return True
    
    async def prompt_user_for_download(self, message: Message, url: str, metadata: Dict):
        """Prompt user to confirm download"""
        try:
            user_id = message.from_user.id
            
            # Create confirmation buttons
            btn = ButtonMaker()
            btn.ibutton("✅ Download", f"autodown_yes_{user_id}_{hash(url) % 10000}")
            btn.ibutton("❌ Skip", f"autodown_no_{user_id}_{hash(url) % 10000}")
            btn.ibutton("⚙️ Settings", f"autodown_settings_{user_id}")
            
            # Store URL for callback
            self.user_confirmations[f"{user_id}_{hash(url) % 10000}"] = {
                'url': url,
                'metadata': metadata,
                'message': message
            }
            
            # Create info message
            domain = metadata.get('domain', 'Unknown')
            url_type = metadata.get('estimated_type', 'unknown')
            
            prompt_text = (
                f"🔗 <b>URL Detected</b>\n\n"
                f"<b>Domain:</b> <code>{domain}</code>\n"
                f"<b>Type:</b> <code>{url_type}</code>\n"
                f"<b>URL:</b> <code>{url[:50]}...</code>\n\n"
                f"Would you like to download this?"
            )
            
            await sendMessage(message, prompt_text, btn.build_menu(2))
            
        except Exception as e:
            LOGGER.error(f"Error prompting user for download: {str(e)}")
    
    async def initiate_auto_download(self, message: Message, url: str, metadata: Dict):
        """Initiate automatic download for a URL"""
        try:
            # Add to processing set
            self.processing_urls.add(url)
            
            # Send notification
            domain = metadata.get('domain', 'Unknown')
            url_type = metadata.get('estimated_type', 'unknown')
            
            notification = (
                f"🤖 <b>Auto-Download Started</b>\n\n"
                f"<b>Domain:</b> <code>{domain}</code>\n"
                f"<b>Type:</b> <code>{url_type}</code>\n"
                f"<b>URL:</b> <code>{url[:50]}...</code>"
            )
            
            status_msg = await sendMessage(message, notification)
            
            # Process the download
            success = await url_detector.process_auto_download(url, message)
            
            if success:
                await editMessage(status_msg, notification + "\n\n✅ <i>Download initiated successfully!</i>")
                # Auto-delete notification after 10 seconds
                asyncio.create_task(self.auto_delete_message(status_msg, 10))
            else:
                await editMessage(status_msg, notification + "\n\n❌ <i>Failed to initiate download.</i>")
                asyncio.create_task(self.auto_delete_message(status_msg, 5))
            
        except Exception as e:
            LOGGER.error(f"Error initiating auto-download for {url}: {str(e)}")
        finally:
            # Remove from processing set
            self.processing_urls.discard(url)
    
    async def auto_delete_message(self, message, delay: int):
        """Auto-delete a message after specified delay"""
        try:
            await asyncio.sleep(delay)
            await deleteMessage(message)
        except Exception:
            pass

# Global instance
auto_download_manager = AutoDownloadManager()

@new_task
async def auto_download_handler(_, message: Message):
    """Handle messages for auto-download detection"""
    # Skip if message is from bot or is a command
    if message.from_user.is_bot or (message.text and message.text.startswith('/')):
        return
    
    # Skip if user hasn't enabled auto-download
    user_id = message.from_user.id
    if user_id in user_data:
        auto_prefs = user_data[user_id].get('auto_download', {})
        if not auto_prefs.get('enabled', False) and not auto_prefs.get('prompt_enabled', True):
            return
    
    # Process URLs in the message
    await auto_download_manager.process_message_urls(message)

@new_task
async def auto_download_callback(_, query):
    """Handle auto-download callback queries"""
    data = query.data.split("_")
    user_id = query.from_user.id
    
    if user_id != int(data[2]):
        await query.answer("❌ Not your request!", show_alert=True)
        return
    
    action = data[1]
    url_hash = data[3] if len(data) > 3 else None
    
    if action == "yes" and url_hash:
        # User confirmed download
        confirmation_key = f"{user_id}_{url_hash}"
        if confirmation_key in auto_download_manager.user_confirmations:
            confirmation_data = auto_download_manager.user_confirmations[confirmation_key]
            url = confirmation_data['url']
            metadata = confirmation_data['metadata']
            original_message = confirmation_data['message']
            
            await query.answer("✅ Download started!")
            await auto_download_manager.initiate_auto_download(original_message, url, metadata)
            
            # Clean up
            del auto_download_manager.user_confirmations[confirmation_key]
            await deleteMessage(query.message)
    
    elif action == "no" and url_hash:
        # User declined download
        confirmation_key = f"{user_id}_{url_hash}"
        if confirmation_key in auto_download_manager.user_confirmations:
            del auto_download_manager.user_confirmations[confirmation_key]
        
        await query.answer("❌ Download skipped!")
        await deleteMessage(query.message)
    
    elif action == "settings":
        # Show auto-download settings
        await show_auto_download_settings(query)

async def show_auto_download_settings(query):
    """Show auto-download settings to user"""
    user_id = query.from_user.id
    
    # Get current settings
    current_settings = user_data.get(user_id, {}).get('auto_download', {
        'enabled': False,
        'prompt_enabled': True,
        'allowed_types': ['gdrive', 'mega', 'youtube'],
        'domain_whitelist': [],
        'domain_blacklist': []
    })
    
    # Create settings buttons
    btn = ButtonMaker()
    
    enabled_text = "✅ Enabled" if current_settings['enabled'] else "❌ Disabled"
    prompt_text = "✅ Enabled" if current_settings['prompt_enabled'] else "❌ Disabled"
    
    btn.ibutton(f"Auto-Download: {enabled_text}", f"autosetting_toggle_{user_id}")
    btn.ibutton(f"Prompts: {prompt_text}", f"autosetting_prompt_{user_id}")
    btn.ibutton("📋 Allowed Types", f"autosetting_types_{user_id}")
    btn.ibutton("🏠 Domain Settings", f"autosetting_domains_{user_id}")
    btn.ibutton("❌ Close", f"autosetting_close_{user_id}")
    
    settings_text = (
        f"⚙️ <b>Auto-Download Settings</b>\n\n"
        f"<b>Status:</b> {enabled_text}\n"
        f"<b>Prompts:</b> {prompt_text}\n"
        f"<b>Allowed Types:</b> {', '.join(current_settings['allowed_types'])}\n"
        f"<b>Whitelisted Domains:</b> {len(current_settings['domain_whitelist'])}\n"
        f"<b>Blacklisted Domains:</b> {len(current_settings['domain_blacklist'])}"
    )
    
    await query.edit_message_text(settings_text, reply_markup=btn.build_menu(1))

# Register handlers
bot.add_handler(MessageHandler(auto_download_handler, 
                              filters.text | filters.caption))

# Register callback handler for auto-download buttons
from pyrogram.handlers import CallbackQueryHandler
bot.add_handler(CallbackQueryHandler(auto_download_callback, 
                                   filters.regex(r"^autodown_")))

LOGGER.info("Auto-Download module loaded successfully!")