#!/usr/bin/env python3
"""
NSFW Filter Integration Module

This module integrates NSFW content filtering with the download system,
auto-download features, and message processing to provide comprehensive
protection against adult content.
"""

import asyncio
from typing import Dict, List, Optional
from pyrogram.types import Message

from bot import LOGGER, user_data
from bot.helper.ext_utils.nsfw_filter import (
    nsfw_filter,
    scan_url_for_nsfw,
    is_nsfw_blocked,
    report_false_positive,
    report_missed_content
)
from bot.helper.ext_utils.url_auto_detector import detect_urls_in_message
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import new_task

class NSFWIntegration:
    """Integration layer for NSFW filtering with download systems"""
    
    def __init__(self):
        self.blocked_urls = {}  # Track blocked URLs for reporting
        self.override_requests = {}  # Track user override requests
        
    async def check_url_before_download(self, url: str, user_id: int, title: str = "", description: str = "") -> Dict:
        """
        Check URL for NSFW content before allowing download
        
        Args:
            url: URL to check
            user_id: User requesting download
            title: Optional content title
            description: Optional content description
            
        Returns:
            Dictionary with check results and action needed
        """
        try:
            # Scan the URL
            scan_result = await scan_url_for_nsfw(url, title, description)
            
            # Check if content should be blocked for this user
            should_block = is_nsfw_blocked(user_id, scan_result)
            
            # Get user settings
            user_settings = user_data.get(user_id, {}).get('nsfw_filter', {})
            
            result = {
                'allowed': not should_block,
                'blocked': should_block,
                'scan_result': scan_result,
                'action': 'allow',  # allow, block, warn, override_available
                'message': '',
                'buttons': None
            }
            
            if should_block:
                # Store blocked URL for potential reporting
                self.blocked_urls[f"{user_id}_{hash(url)}"] = {
                    'url': url,
                    'user_id': user_id,
                    'scan_result': scan_result,
                    'timestamp': asyncio.get_event_loop().time()
                }
                
                # Check if user can override
                if user_settings.get('allow_override', False):
                    result['action'] = 'override_available'
                    result['message'] = self._create_override_message(url, scan_result)
                    result['buttons'] = self._create_override_buttons(user_id, url)
                else:
                    result['action'] = 'block'
                    result['message'] = self._create_block_message(url, scan_result)
                    result['buttons'] = self._create_report_buttons(user_id, url)
            
            elif scan_result['is_nsfw'] and user_settings.get('show_warnings', True):
                # Show warning for potentially NSFW content
                result['action'] = 'warn'
                result['message'] = self._create_warning_message(url, scan_result)
                result['buttons'] = self._create_warning_buttons(user_id, url)
            
            return result
            
        except Exception as e:
            LOGGER.error(f"Error checking URL for NSFW: {str(e)}")
            return {
                'allowed': True,  # Allow on error to avoid blocking legitimate content
                'blocked': False,
                'action': 'allow',
                'message': '',
                'buttons': None,
                'error': str(e)
            }
    
    def _create_block_message(self, url: str, scan_result: Dict) -> str:
        """Create message for blocked content"""
        domain = url.split('/')[2] if '/' in url else url
        confidence = scan_result['confidence']
        
        message = (
            f"🚫 <b>NSFW Content Blocked</b>\n\n"
            f"<b>Domain:</b> <code>{domain}</code>\n"
            f"<b>Confidence:</b> {confidence:.0%}\n"
            f"<b>Reason:</b> Adult content detected\n\n"
            f"<i>This URL has been blocked to protect against NSFW content. "
            f"If this is a false positive, you can report it.</i>"
        )
        
        return message
    
    def _create_warning_message(self, url: str, scan_result: Dict) -> str:
        """Create message for warning about potentially NSFW content"""
        domain = url.split('/')[2] if '/' in url else url
        confidence = scan_result['confidence']
        
        message = (
            f"⚠️ <b>Potentially NSFW Content</b>\n\n"
            f"<b>Domain:</b> <code>{domain}</code>\n"
            f"<b>Confidence:</b> {confidence:.0%}\n"
            f"<b>Status:</b> Allowed but flagged\n\n"
            f"<i>This content may contain adult material. Download will proceed normally.</i>"
        )
        
        return message
    
    def _create_override_message(self, url: str, scan_result: Dict) -> str:
        """Create message for override request"""
        domain = url.split('/')[2] if '/' in url else url
        confidence = scan_result['confidence']
        
        message = (
            f"🛑 <b>NSFW Content Detected</b>\n\n"
            f"<b>Domain:</b> <code>{domain}</code>\n"
            f"<b>Confidence:</b> {confidence:.0%}\n"
            f"<b>Status:</b> Blocked by filter\n\n"
            f"<i>You can override this block if you believe this is safe content.</i>"
        )
        
        return message
    
    def _create_override_buttons(self, user_id: int, url: str) -> ButtonMaker:
        """Create buttons for override request"""
        btn = ButtonMaker()
        url_hash = hash(url) % 10000
        
        btn.ibutton("✅ Override & Download", f"nsfw_override_{user_id}_{url_hash}")
        btn.ibutton("❌ Keep Blocked", f"nsfw_keep_blocked_{user_id}_{url_hash}")
        btn.ibutton("📝 Report False Positive", f"nsfw_report_fp_{user_id}_{url_hash}")
        
        return btn
    
    def _create_report_buttons(self, user_id: int, url: str) -> ButtonMaker:
        """Create buttons for reporting"""
        btn = ButtonMaker()
        url_hash = hash(url) % 10000
        
        btn.ibutton("📝 Report False Positive", f"nsfw_report_fp_{user_id}_{url_hash}")
        btn.ibutton("⚙️ Adjust Settings", f"nsfw_settings_{user_id}")
        
        return btn
    
    def _create_warning_buttons(self, user_id: int, url: str) -> ButtonMaker:
        """Create buttons for warning message"""
        btn = ButtonMaker()
        url_hash = hash(url) % 10000
        
        btn.ibutton("📝 Report if Safe", f"nsfw_report_fp_{user_id}_{url_hash}")
        btn.ibutton("🚫 Report if NSFW", f"nsfw_report_missed_{user_id}_{url_hash}")
        
        return btn
    
    async def handle_override_request(self, user_id: int, url_hash: str, action: str) -> bool:
        """
        Handle user override request
        
        Args:
            user_id: User ID
            url_hash: Hashed URL identifier
            action: override, keep_blocked, report_fp, report_missed
            
        Returns:
            Boolean indicating if download should proceed
        """
        blocked_key = f"{user_id}_{url_hash}"
        
        if blocked_key not in self.blocked_urls:
            return False
        
        blocked_data = self.blocked_urls[blocked_key]
        url = blocked_data['url']
        
        if action == "override":
            # User chose to override the block
            LOGGER.info(f"User {user_id} overrode NSFW block for: {url}")
            del self.blocked_urls[blocked_key]
            return True
            
        elif action == "keep_blocked":
            # User confirmed the block
            del self.blocked_urls[blocked_key]
            return False
            
        elif action == "report_fp":
            # User reported false positive
            report_false_positive(url, user_id)
            del self.blocked_urls[blocked_key]
            return True  # Allow download after reporting
            
        elif action == "report_missed":
            # User reported missed NSFW content
            report_missed_content(url, user_id)
            return False
        
        return False
    
    async def scan_message_for_nsfw(self, message: Message) -> List[Dict]:
        """
        Scan message for NSFW URLs and content
        
        Args:
            message: Telegram message to scan
            
        Returns:
            List of scan results for each URL found
        """
        try:
            # Extract URLs from message
            text = message.text or message.caption or ""
            urls = detect_urls_in_message(text)
            
            if not urls:
                return []
            
            scan_results = []
            
            for url, metadata in urls:
                # Scan each URL
                scan_result = await scan_url_for_nsfw(url, text, "")
                
                scan_results.append({
                    'url': url,
                    'metadata': metadata,
                    'scan_result': scan_result,
                    'blocked': is_nsfw_blocked(message.from_user.id, scan_result)
                })
            
            return scan_results
            
        except Exception as e:
            LOGGER.error(f"Error scanning message for NSFW: {str(e)}")
            return []
    
    async def handle_nsfw_message(self, message: Message, scan_results: List[Dict]):
        """
        Handle message containing NSFW content
        
        Args:
            message: Original message
            scan_results: Results from scanning
        """
        user_id = message.from_user.id
        user_settings = user_data.get(user_id, {}).get('nsfw_filter', {})
        
        # Check if any URLs are blocked
        blocked_urls = [result for result in scan_results if result['blocked']]
        
        if not blocked_urls:
            return
        
        # Handle based on user settings
        if user_settings.get('auto_delete_nsfw', False):
            # Delete the message
            try:
                await deleteMessage(message)
                
                # Send notification
                notification = (
                    f"🗑️ <b>NSFW Message Deleted</b>\n\n"
                    f"A message containing {len(blocked_urls)} NSFW URL(s) was automatically deleted.\n\n"
                    f"<i>You can disable auto-delete in NSFW filter settings.</i>"
                )
                
                await sendMessage(message, notification)
                
            except Exception as e:
                LOGGER.error(f"Failed to delete NSFW message: {str(e)}")
        
        elif user_settings.get('show_warnings', True):
            # Show warning about NSFW content
            warning_text = (
                f"⚠️ <b>NSFW Content Detected</b>\n\n"
                f"Your message contains {len(blocked_urls)} URL(s) flagged as adult content:\n\n"
            )
            
            for i, result in enumerate(blocked_urls[:3], 1):
                domain = result['url'].split('/')[2] if '/' in result['url'] else result['url']
                confidence = result['scan_result']['confidence']
                warning_text += f"{i}. {domain} ({confidence:.0%})\n"
            
            if len(blocked_urls) > 3:
                warning_text += f"... and {len(blocked_urls) - 3} more\n"
            
            warning_text += f"\n<i>Downloads from these URLs will be blocked.</i>"
            
            btn = ButtonMaker()
            btn.ibutton("⚙️ NSFW Settings", f"nsfw_settings_{user_id}")
            
            await sendMessage(message, warning_text, btn.build_menu(1))

# Global integration instance
nsfw_integration = NSFWIntegration()

# Integration functions for other modules
async def check_nsfw_before_download(url: str, user_id: int, title: str = "", description: str = "") -> Dict:
    """Check if URL should be blocked before download"""
    return await nsfw_integration.check_url_before_download(url, user_id, title, description)

async def scan_message_nsfw(message: Message) -> List[Dict]:
    """Scan message for NSFW content"""
    return await nsfw_integration.scan_message_for_nsfw(message)

async def handle_nsfw_in_message(message: Message, scan_results: List[Dict]):
    """Handle NSFW content in message"""
    await nsfw_integration.handle_nsfw_message(message, scan_results)

# Callback handler for NSFW integration buttons
@new_task
async def nsfw_integration_callback(_, query):
    """Handle NSFW integration callbacks"""
    data = query.data.split("_")
    
    if len(data) < 4:
        return
    
    user_id = query.from_user.id
    action = data[2]  # override, keep_blocked, report_fp, report_missed
    target_user = int(data[3])
    url_hash = data[4] if len(data) > 4 else ""
    
    if user_id != target_user:
        await query.answer("❌ Not your request!", show_alert=True)
        return
    
    try:
        if action in ["override", "keep_blocked", "report_fp", "report_missed"]:
            should_proceed = await nsfw_integration.handle_override_request(
                user_id, url_hash, action
            )
            
            if action == "override" and should_proceed:
                await query.answer("✅ Block overridden. Download will proceed.")
                await deleteMessage(query.message)
            elif action == "keep_blocked":
                await query.answer("🚫 Content remains blocked.")
                await deleteMessage(query.message)
            elif action == "report_fp":
                await query.answer("📝 False positive reported. Thank you!")
                await deleteMessage(query.message)
            elif action == "report_missed":
                await query.answer("📝 Missed content reported. Thank you!")
                await deleteMessage(query.message)
        
        elif action == "settings":
            # Redirect to NSFW settings
            from bot.modules.nsfw_settings import show_nsfw_settings
            await show_nsfw_settings(query.message)
            await deleteMessage(query.message)
    
    except Exception as e:
        LOGGER.error(f"Error in NSFW integration callback: {str(e)}")
        await query.answer("❌ An error occurred!", show_alert=True)

# Register callback handler
from bot import bot
from pyrogram.handlers import CallbackQueryHandler
from pyrogram import filters

bot.add_handler(CallbackQueryHandler(nsfw_integration_callback, 
                                   filters.regex(r"^nsfw_(override|keep_blocked|report_fp|report_missed|settings)_")))

LOGGER.info("NSFW Integration module loaded successfully!")