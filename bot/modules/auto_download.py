#!/usr/bin/env python3
"""
Auto-Download Module for WZML-X Bot

This module handles automatic detection and downloading of supported URLs
from user messages without requiring explicit commands.
"""



from typing import Dict
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
from bot.modules.nsfw_integration import (
    check_nsfw_before_download,
    scan_message_nsfw,
    handle_nsfw_in_message
)
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, editMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import new_task, update_user_ldata
from bot.helper.telegram_helper.bot_commands import BotCommands

# =====================
# Settings (merged)
# =====================

DEFAULT_AUTO_DOWNLOAD_SETTINGS = {
    'enabled': False,
    'prompt_enabled': True,
    'allowed_types': ['gdrive', 'mega', 'youtube', 'torrent_file', 'magnet'],
    'domain_whitelist': [],
    'domain_blacklist': [],
    'max_size_mb': 0,
    'auto_extract': False,
    'auto_compress': False,
    'notification_level': 'normal'
}

URL_TYPE_DESCRIPTIONS = {
    'gdrive': '🔷 Google Drive',
    'mega': '🔶 Mega.nz',
    'youtube': '🎬 YouTube/Video Sites', 
    'torrent_file': '📁 Torrent Files',
    'magnet': '🧲 Magnet Links',
    'telegram': '💬 Telegram Files',
    'filehost': '📂 File Hosting Sites',
    'direct': '🔗 Direct Download Links',
    'cloud': '☁️ Cloud Storage',
    'video': '🎥 Video Streaming',
    'http': '🌐 HTTP/HTTPS URLs',
    'ftp': '📡 FTP Links'
}

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
            
            # First, scan message for NSFW content
            nsfw_scan_results = await scan_message_nsfw(message)
            
            # Handle NSFW content in message
            if nsfw_scan_results:
                await handle_nsfw_in_message(message, nsfw_scan_results)
            
            # Filter URLs that should be auto-downloaded
            downloadable_urls = []
            for url, metadata in urls:
                if url not in self.processing_urls:
                    # Check NSFW before processing
                    nsfw_check = await check_nsfw_before_download(
                        url, user_id, 
                        message.text or message.caption or ""
                    )
                    
                    if nsfw_check['blocked']:
                        # Handle blocked NSFW content
                        if nsfw_check['message']:
                            await sendMessage(
                                message, 
                                nsfw_check['message'], 
                                nsfw_check['buttons'].build_menu(1) if nsfw_check['buttons'] else None
                            )
                        continue
                    
                    # Show NSFW warning if needed
                    if nsfw_check['action'] == 'warn' and nsfw_check['message']:
                        await sendMessage(
                            message,
                            nsfw_check['message'],
                            nsfw_check['buttons'].build_menu(1) if nsfw_check['buttons'] else None
                        )
                    
                    # Continue with normal processing for allowed URLs
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
            btn.ibutton("⚙️ Settings", f"ads_back_{user_id}")
            
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
            
            # Directly process the download without queueing
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

## Queue-based integration removed as requested

# =====================
# Settings commands/UI (merged)
# =====================

@new_task
async def auto_download_settings_cmd(_, message: Message):
    """Handle /autodownload command (merged)"""
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {}
    if 'auto_download' not in user_data[user_id]:
        user_data[user_id]['auto_download'] = DEFAULT_AUTO_DOWNLOAD_SETTINGS.copy()
        update_user_ldata(user_id, 'auto_download', user_data[user_id]['auto_download'])
    await show_main_settings(message)

async def show_main_settings(message: Message):
    user_id = message.from_user.id
    settings = user_data[user_id]['auto_download']
    btn = ButtonMaker()
    enabled_text = "✅ Enabled" if settings['enabled'] else "❌ Disabled"
    prompt_text = "✅ Enabled" if settings['prompt_enabled'] else "❌ Disabled"
    extract_text = "✅ Enabled" if settings.get('auto_extract', False) else "❌ Disabled"
    compress_text = "✅ Enabled" if settings.get('auto_compress', False) else "❌ Disabled"
    btn.ibutton(f"Auto-Download: {enabled_text}", f"ads_toggle_enabled_{user_id}")
    btn.ibutton(f"Confirmation Prompts: {prompt_text}", f"ads_toggle_prompt_{user_id}")
    btn.ibutton(f"Auto-Extract: {extract_text}", f"ads_toggle_extract_{user_id}")
    btn.ibutton(f"Auto-Compress: {compress_text}", f"ads_toggle_compress_{user_id}")
    btn.ibutton("📋 URL Types", f"ads_types_{user_id}")
    btn.ibutton("🌐 Domain Settings", f"ads_domains_{user_id}")
    btn.ibutton("📏 Size Limits", f"ads_size_{user_id}")
    btn.ibutton("🔔 Notifications", f"ads_notifications_{user_id}")
    btn.ibutton("ℹ️ Help", f"ads_help_{user_id}")
    btn.ibutton("❌ Close", f"ads_close_{user_id}")
    status_text = (
        f"⚙️ <b>Auto-Download Settings</b>\n\n"
        f"<b>Status:</b> {enabled_text}\n"
        f"<b>Confirmation Prompts:</b> {prompt_text}\n"
        f"<b>Allowed URL Types:</b> {len(settings['allowed_types'])}\n"
        f"<b>Whitelisted Domains:</b> {len(settings['domain_whitelist'])}\n"
        f"<b>Blacklisted Domains:</b> {len(settings['domain_blacklist'])}\n"
        f"<b>Size Limit:</b> {'No limit' if settings.get('max_size_mb', 0) == 0 else str(settings['max_size_mb']) + ' MB'}\n"
        f"<b>Auto-Extract:</b> {extract_text}\n"
        f"<b>Auto-Compress:</b> {compress_text}\n"
        f"<b>Notification Level:</b> {settings.get('notification_level', 'normal').title()}"
    )
    await sendMessage(message, status_text, btn.build_menu(2))

async def show_url_types_settings(query):
    user_id = query.from_user.id
    settings = user_data[user_id]['auto_download']
    btn = ButtonMaker()
    for url_type, description in URL_TYPE_DESCRIPTIONS.items():
        is_enabled = url_type in settings['allowed_types']
        status = "✅" if is_enabled else "❌"
        btn.ibutton(f"{status} {description}", f"ads_type_toggle_{user_id}_{url_type}")
    btn.ibutton("✅ Enable All", f"ads_types_all_{user_id}")
    btn.ibutton("❌ Disable All", f"ads_types_none_{user_id}")
    btn.ibutton("🔧 Safe Only", f"ads_types_safe_{user_id}")
    btn.ibutton("⬅️ Back", f"ads_back_{user_id}")
    types_text = (
        f"📋 <b>URL Types Configuration</b>\n\n"
        f"Select which types of URLs should be automatically downloaded:\n\n"
        f"<b>Currently Enabled:</b> {len(settings['allowed_types'])} types\n"
        f"<b>Safe Types:</b> Google Drive, Mega, YouTube, Torrent files"
    )
    await query.edit_message_text(types_text, reply_markup=btn.build_menu(1))

async def show_domain_settings(query):
    user_id = query.from_user.id
    settings = user_data[user_id]['auto_download']
    btn = ButtonMaker()
    btn.ibutton("✅ Manage Whitelist", f"ads_whitelist_{user_id}")
    btn.ibutton("❌ Manage Blacklist", f"ads_blacklist_{user_id}")
    btn.ibutton("🧹 Clear All", f"ads_clear_domains_{user_id}")
    btn.ibutton("⬅️ Back", f"ads_back_{user_id}")
    domain_text = (
        f"🌐 <b>Domain Settings</b>\n\n"
        f"<b>Whitelist:</b> {len(settings['domain_whitelist'])} domains\n"
        f"<i>Only URLs from these domains will be auto-downloaded</i>\n\n"
        f"<b>Blacklist:</b> {len(settings['domain_blacklist'])} domains\n"
        f"<i>URLs from these domains will never be auto-downloaded</i>\n\n"
        f"<b>Note:</b> If whitelist is empty, all domains are allowed (except blacklisted)"
    )
    if settings['domain_whitelist']:
        domain_text += f"\n\n<b>Whitelisted:</b>\n• " + "\n• ".join(settings['domain_whitelist'][:5])
        if len(settings['domain_whitelist']) > 5:
            domain_text += f"\n• ... and {len(settings['domain_whitelist']) - 5} more"
    if settings['domain_blacklist']:
        domain_text += f"\n\n<b>Blacklisted:</b>\n• " + "\n• ".join(settings['domain_blacklist'][:5])
        if len(settings['domain_blacklist']) > 5:
            domain_text += f"\n• ... and {len(settings['domain_blacklist']) - 5} more"
    await query.edit_message_text(domain_text, reply_markup=btn.build_menu(1))

async def show_help(query):
    user_id = query.from_user.id
    btn = ButtonMaker()
    btn.ibutton("⬅️ Back", f"ads_back_{user_id}")
    help_text = (
        f"ℹ️ <b>Auto-Download Help</b>\n\n"
        f"<b>How it works:</b>\n"
        f"• The bot automatically detects supported URLs in messages\n"
        f"• Based on your settings, it either downloads immediately or asks for confirmation\n"
        f"• You can configure which types of URLs to auto-download\n\n"
        f"<b>URL Types:</b>\n"
        f"• <b>Safe:</b> Google Drive, Mega, YouTube, Torrent files\n"
        f"• <b>Moderate:</b> Telegram files, popular file hosts\n"
        f"• <b>Caution:</b> Direct HTTP links, unknown domains\n\n"
        f"<b>Domain Settings:</b>\n"
        f"• <b>Whitelist:</b> Only allow specific domains\n"
        f"• <b>Blacklist:</b> Block specific domains\n\n"
        f"<b>Size Limits:</b>\n"
        f"• Set maximum file size for auto-downloads\n"
        f"• Larger files will require confirmation\n\n"
        f"<b>Commands:</b>\n"
        f"• <code>/autodownload</code> - Open settings\n"
        f"• <code>/adstats</code> - View statistics"
    )
    await query.edit_message_text(help_text, reply_markup=btn.build_menu(1))

@new_task
async def auto_download_settings_callback_handler(_, query):
    data = query.data.split("_")
    if len(data) < 3:
        return
    user_id = query.from_user.id
    action = data[1]
    target_user = int(data[2])
    if user_id != target_user:
        await query.answer("❌ Not your settings!", show_alert=True)
        return
    settings = user_data[user_id]['auto_download']
    try:
        if action == "toggle":
            setting_name = data[3]
            if setting_name == "enabled":
                settings['enabled'] = not settings['enabled']
            elif setting_name == "prompt":
                settings['prompt_enabled'] = not settings['prompt_enabled']
            elif setting_name == "extract":
                settings['auto_extract'] = not settings['auto_extract']
            elif setting_name == "compress":
                settings['auto_compress'] = not settings['auto_compress']
            update_user_ldata(user_id, 'auto_download', settings)
            await show_main_settings_edit(query)
        elif action == "types":
            await show_url_types_settings(query)
        elif action == "domains":
            await show_domain_settings(query)
        elif action == "help":
            await show_help(query)
        elif action == "back":
            await show_main_settings_edit(query)
        elif action == "close":
            await deleteMessage(query.message)
        elif action == "type" and len(data) > 4:
            url_type = data[4]
            if url_type in settings['allowed_types']:
                settings['allowed_types'].remove(url_type)
            else:
                settings['allowed_types'].append(url_type)
            update_user_ldata(user_id, 'auto_download', settings)
            await show_url_types_settings(query)
        elif action == "types" and len(data) > 3:
            if data[3] == "all":
                settings['allowed_types'] = list(URL_TYPE_DESCRIPTIONS.keys())
            elif data[3] == "none":
                settings['allowed_types'] = []
            elif data[3] == "safe":
                settings['allowed_types'] = ['gdrive', 'mega', 'youtube', 'torrent_file', 'magnet']
            update_user_ldata(user_id, 'auto_download', settings)
            await show_url_types_settings(query)
        await query.answer()
    except Exception as e:
        LOGGER.error(f"Error in auto-download callback: {str(e)}")
        await query.answer("❌ An error occurred!", show_alert=True)

async def show_main_settings_edit(query):
    user_id = query.from_user.id
    settings = user_data[user_id]['auto_download']
    btn = ButtonMaker()
    enabled_text = "✅ Enabled" if settings['enabled'] else "❌ Disabled"
    prompt_text = "✅ Enabled" if settings['prompt_enabled'] else "❌ Disabled"
    extract_text = "✅ Enabled" if settings.get('auto_extract', False) else "❌ Disabled"
    compress_text = "✅ Enabled" if settings.get('auto_compress', False) else "❌ Disabled"
    btn.ibutton(f"Auto-Download: {enabled_text}", f"ads_toggle_enabled_{user_id}")
    btn.ibutton(f"Confirmation Prompts: {prompt_text}", f"ads_toggle_prompt_{user_id}")
    btn.ibutton(f"Auto-Extract: {extract_text}", f"ads_toggle_extract_{user_id}")
    btn.ibutton(f"Auto-Compress: {compress_text}", f"ads_toggle_compress_{user_id}")
    btn.ibutton("📋 URL Types", f"ads_types_{user_id}")
    btn.ibutton("🌐 Domain Settings", f"ads_domains_{user_id}")
    btn.ibutton("📏 Size Limits", f"ads_size_{user_id}")
    btn.ibutton("🔔 Notifications", f"ads_notifications_{user_id}")
    btn.ibutton("ℹ️ Help", f"ads_help_{user_id}")
    btn.ibutton("❌ Close", f"ads_close_{user_id}")
    status_text = (
        f"⚙️ <b>Auto-Download Settings</b>\n\n"
        f"<b>Status:</b> {enabled_text}\n"
        f"<b>Confirmation Prompts:</b> {prompt_text}\n"
        f"<b>Allowed URL Types:</b> {len(settings['allowed_types'])}\n"
        f"<b>Whitelisted Domains:</b> {len(settings['domain_whitelist'])}\n"
        f"<b>Blacklisted Domains:</b> {len(settings['domain_blacklist'])}\n"
        f"<b>Size Limit:</b> {'No limit' if settings.get('max_size_mb', 0) == 0 else str(settings['max_size_mb']) + ' MB'}\n"
        f"<b>Auto-Extract:</b> {extract_text}\n"
        f"<b>Auto-Compress:</b> {compress_text}\n"
        f"<b>Notification Level:</b> {settings.get('notification_level', 'normal').title()}"
    )
    await query.edit_message_text(status_text, reply_markup=btn.build_menu(2))

# Backward-compat for old settings entry point
async def show_auto_download_settings(query):
    await show_main_settings_edit(query)
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
        await show_main_settings_edit(query)

    # removed legacy inline settings; unified under ads_ handlers

from pyrogram.handlers import CallbackQueryHandler

# Register handlers (messages)
bot.add_handler(MessageHandler(
    auto_download_handler,
    (filters.text | filters.caption)
    & ~CustomFilters.blacklisted
))

# Register auto-download inline callbacks
bot.add_handler(CallbackQueryHandler(
    auto_download_callback,
    filters.regex(r"^autodown_")
))

# Register settings command and settings callbacks
bot.add_handler(MessageHandler(
    auto_download_settings_cmd,
    filters.command(BotCommands.AutoDownloadCommand) & CustomFilters.authorized
))
bot.add_handler(CallbackQueryHandler(
    auto_download_settings_callback_handler,
    filters.regex(r"^ads_")
))

LOGGER.info("Auto-Download module loaded successfully!")