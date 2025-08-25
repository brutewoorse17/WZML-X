#!/usr/bin/env python3
"""
Auto-Download Settings Module for WZML-X Bot

This module handles user preferences and settings for the auto-download feature.
Users can configure which types of URLs to auto-download, domain preferences, etc.
"""

from pyrogram import filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message

from bot import bot, LOGGER, user_data
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.bot_utils import new_task, update_user_ldata
from bot.helper.ext_utils.db_handler import DbManger

# Default auto-download settings
DEFAULT_AUTO_DOWNLOAD_SETTINGS = {
    'enabled': False,
    'prompt_enabled': True,
    'allowed_types': ['gdrive', 'mega', 'youtube', 'torrent_file', 'magnet'],
    'domain_whitelist': [],
    'domain_blacklist': [],
    'max_size_mb': 0,  # 0 means no limit
    'auto_extract': False,
    'auto_compress': False,
    'notification_level': 'normal'  # 'silent', 'normal', 'verbose'
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

@new_task
async def auto_download_settings_cmd(_, message: Message):
    """Handle /autodownload command"""
    user_id = message.from_user.id
    
    # Initialize user settings if not exists
    if user_id not in user_data:
        user_data[user_id] = {}
    
    if 'auto_download' not in user_data[user_id]:
        user_data[user_id]['auto_download'] = DEFAULT_AUTO_DOWNLOAD_SETTINGS.copy()
        update_user_ldata(user_id, 'auto_download', user_data[user_id]['auto_download'])
    
    await show_main_settings(message)

async def show_main_settings(message: Message):
    """Show main auto-download settings menu"""
    user_id = message.from_user.id
    settings = user_data[user_id]['auto_download']
    
    btn = ButtonMaker()
    
    # Toggle buttons
    enabled_text = "✅ Enabled" if settings['enabled'] else "❌ Disabled"
    prompt_text = "✅ Enabled" if settings['prompt_enabled'] else "❌ Disabled"
    extract_text = "✅ Enabled" if settings['auto_extract'] else "❌ Disabled"
    compress_text = "✅ Enabled" if settings['auto_compress'] else "❌ Disabled"
    
    btn.ibutton(f"Auto-Download: {enabled_text}", f"ads_toggle_enabled_{user_id}")
    btn.ibutton(f"Confirmation Prompts: {prompt_text}", f"ads_toggle_prompt_{user_id}")
    btn.ibutton(f"Auto-Extract: {extract_text}", f"ads_toggle_extract_{user_id}")
    btn.ibutton(f"Auto-Compress: {compress_text}", f"ads_toggle_compress_{user_id}")
    
    # Configuration buttons
    btn.ibutton("📋 URL Types", f"ads_types_{user_id}")
    btn.ibutton("🌐 Domain Settings", f"ads_domains_{user_id}")
    btn.ibutton("📏 Size Limits", f"ads_size_{user_id}")
    btn.ibutton("🔔 Notifications", f"ads_notifications_{user_id}")
    
    # Info and close
    btn.ibutton("ℹ️ Help", f"ads_help_{user_id}")
    btn.ibutton("❌ Close", f"ads_close_{user_id}")
    
    # Build status text
    status_text = (
        f"⚙️ <b>Auto-Download Settings</b>\n\n"
        f"<b>Status:</b> {enabled_text}\n"
        f"<b>Confirmation Prompts:</b> {prompt_text}\n"
        f"<b>Allowed URL Types:</b> {len(settings['allowed_types'])}\n"
        f"<b>Whitelisted Domains:</b> {len(settings['domain_whitelist'])}\n"
        f"<b>Blacklisted Domains:</b> {len(settings['domain_blacklist'])}\n"
        f"<b>Size Limit:</b> {'No limit' if settings['max_size_mb'] == 0 else f\"{settings['max_size_mb']} MB\"}\n"
        f"<b>Auto-Extract:</b> {extract_text}\n"
        f"<b>Auto-Compress:</b> {compress_text}\n"
        f"<b>Notification Level:</b> {settings['notification_level'].title()}"
    )
    
    await sendMessage(message, status_text, btn.build_menu(2))

async def show_url_types_settings(query):
    """Show URL types configuration"""
    user_id = query.from_user.id
    settings = user_data[user_id]['auto_download']
    
    btn = ButtonMaker()
    
    # Create toggle buttons for each URL type
    for url_type, description in URL_TYPE_DESCRIPTIONS.items():
        is_enabled = url_type in settings['allowed_types']
        status = "✅" if is_enabled else "❌"
        btn.ibutton(f"{status} {description}", f"ads_type_toggle_{user_id}_{url_type}")
    
    # Bulk actions
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
    """Show domain whitelist/blacklist settings"""
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
    """Show auto-download help"""
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
async def auto_download_callback_handler(_, query):
    """Handle auto-download settings callbacks"""
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
            
            # Update database
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
            # Toggle specific URL type
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
    """Show main settings (for edit message)"""
    user_id = query.from_user.id
    settings = user_data[user_id]['auto_download']
    
    btn = ButtonMaker()
    
    # Toggle buttons
    enabled_text = "✅ Enabled" if settings['enabled'] else "❌ Disabled"
    prompt_text = "✅ Enabled" if settings['prompt_enabled'] else "❌ Disabled"
    extract_text = "✅ Enabled" if settings['auto_extract'] else "❌ Disabled"
    compress_text = "✅ Enabled" if settings['auto_compress'] else "❌ Disabled"
    
    btn.ibutton(f"Auto-Download: {enabled_text}", f"ads_toggle_enabled_{user_id}")
    btn.ibutton(f"Confirmation Prompts: {prompt_text}", f"ads_toggle_prompt_{user_id}")
    btn.ibutton(f"Auto-Extract: {extract_text}", f"ads_toggle_extract_{user_id}")
    btn.ibutton(f"Auto-Compress: {compress_text}", f"ads_toggle_compress_{user_id}")
    
    # Configuration buttons
    btn.ibutton("📋 URL Types", f"ads_types_{user_id}")
    btn.ibutton("🌐 Domain Settings", f"ads_domains_{user_id}")
    btn.ibutton("📏 Size Limits", f"ads_size_{user_id}")
    btn.ibutton("🔔 Notifications", f"ads_notifications_{user_id}")
    
    # Info and close
    btn.ibutton("ℹ️ Help", f"ads_help_{user_id}")
    btn.ibutton("❌ Close", f"ads_close_{user_id}")
    
    # Build status text
    status_text = (
        f"⚙️ <b>Auto-Download Settings</b>\n\n"
        f"<b>Status:</b> {enabled_text}\n"
        f"<b>Confirmation Prompts:</b> {prompt_text}\n"
        f"<b>Allowed URL Types:</b> {len(settings['allowed_types'])}\n"
        f"<b>Whitelisted Domains:</b> {len(settings['domain_whitelist'])}\n"
        f"<b>Blacklisted Domains:</b> {len(settings['domain_blacklist'])}\n"
        f"<b>Size Limit:</b> {'No limit' if settings['max_size_mb'] == 0 else f\"{settings['max_size_mb']} MB\"}\n"
        f"<b>Auto-Extract:</b> {extract_text}\n"
        f"<b>Auto-Compress:</b> {compress_text}\n"
        f"<b>Notification Level:</b> {settings['notification_level'].title()}"
    )
    
    await query.edit_message_text(status_text, reply_markup=btn.build_menu(2))

# Register command handler
bot.add_handler(MessageHandler(auto_download_settings_cmd, 
                              filters.command(BotCommands.AutoDownloadCommand) & CustomFilters.authorized))

# Register callback handler
bot.add_handler(CallbackQueryHandler(auto_download_callback_handler, 
                                   filters.regex(r"^ads_")))

LOGGER.info("Auto-Download Settings module loaded successfully!")