#!/usr/bin/env python3
"""
NSFW Filter Settings Module for WZML-X Bot

This module handles user preferences and admin controls for NSFW content filtering.
Users can configure filtering strictness, reporting, and override settings.
"""

from pyrogram import filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message

from bot import bot, LOGGER, user_data, config_dict
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.bot_utils import new_task, update_user_ldata
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.nsfw_filter import nsfw_filter, scan_url_for_nsfw

# Default NSFW filter settings
DEFAULT_NSFW_SETTINGS = {
    'enabled': True,
    'strictness': 'medium',  # off, low, medium, high, strict
    'block_downloads': True,
    'show_warnings': True,
    'allow_override': False,  # Allow user to override blocks
    'report_enabled': True,
    'auto_delete_nsfw': False,
    'whitelist_domains': [],
    'trusted_users': [],  # Users who can bypass filter
}

STRICTNESS_DESCRIPTIONS = {
    'off': '❌ Disabled - No filtering',
    'low': '🟢 Low - Only obvious adult sites',
    'medium': '🟡 Medium - Balanced filtering (Recommended)',
    'high': '🟠 High - Aggressive filtering',
    'strict': '🔴 Strict - Block any suspicious content'
}

@new_task
async def nsfw_settings_cmd(_, message: Message):
    """Handle /nsfwfilter command"""
    user_id = message.from_user.id
    
    # Initialize user settings if not exists
    if user_id not in user_data:
        user_data[user_id] = {}
    
    if 'nsfw_filter' not in user_data[user_id]:
        user_data[user_id]['nsfw_filter'] = DEFAULT_NSFW_SETTINGS.copy()
        update_user_ldata(user_id, 'nsfw_filter', user_data[user_id]['nsfw_filter'])
    
    await show_nsfw_settings(message)

async def show_nsfw_settings(message: Message):
    """Show NSFW filter settings menu"""
    user_id = message.from_user.id
    settings = user_data[user_id]['nsfw_filter']
    
    btn = ButtonMaker()
    
    # Toggle buttons
    enabled_text = "✅ Enabled" if settings['enabled'] else "❌ Disabled"
    downloads_text = "✅ Enabled" if settings['block_downloads'] else "❌ Disabled"
    warnings_text = "✅ Enabled" if settings['show_warnings'] else "❌ Disabled"
    override_text = "✅ Enabled" if settings['allow_override'] else "❌ Disabled"
    reports_text = "✅ Enabled" if settings['report_enabled'] else "❌ Disabled"
    auto_delete_text = "✅ Enabled" if settings['auto_delete_nsfw'] else "❌ Disabled"
    
    strictness_text = STRICTNESS_DESCRIPTIONS[settings['strictness']]
    
    btn.ibutton(f"NSFW Filter: {enabled_text}", f"nsfw_toggle_enabled_{user_id}")
    btn.ibutton(f"Block Downloads: {downloads_text}", f"nsfw_toggle_downloads_{user_id}")
    btn.ibutton(f"Show Warnings: {warnings_text}", f"nsfw_toggle_warnings_{user_id}")
    btn.ibutton(f"Allow Override: {override_text}", f"nsfw_toggle_override_{user_id}")
    
    # Strictness selection
    btn.ibutton("🎚️ Strictness Level", f"nsfw_strictness_{user_id}")
    
    # Advanced options
    btn.ibutton(f"📊 Reporting: {reports_text}", f"nsfw_toggle_reports_{user_id}")
    btn.ibutton(f"🗑️ Auto-Delete: {auto_delete_text}", f"nsfw_toggle_delete_{user_id}")
    btn.ibutton("🏠 Domain Whitelist", f"nsfw_whitelist_{user_id}")
    
    # Testing and stats
    btn.ibutton("🧪 Test URL", f"nsfw_test_{user_id}")
    btn.ibutton("📊 Statistics", f"nsfw_stats_{user_id}")
    btn.ibutton("ℹ️ Help", f"nsfw_help_{user_id}")
    btn.ibutton("❌ Close", f"nsfw_close_{user_id}")
    
    # Build status text
    stats = nsfw_filter.get_stats()
    status_text = (
        f"🛡️ <b>NSFW Content Filter Settings</b>\n\n"
        f"<b>Filter Status:</b> {enabled_text}\n"
        f"<b>Strictness:</b> {strictness_text}\n"
        f"<b>Block Downloads:</b> {downloads_text}\n"
        f"<b>Show Warnings:</b> {warnings_text}\n"
        f"<b>User Override:</b> {override_text}\n"
        f"<b>Reporting:</b> {reports_text}\n"
        f"<b>Auto-Delete:</b> {auto_delete_text}\n\n"
        f"<b>📊 Global Statistics:</b>\n"
        f"• Total Scanned: {stats['total_scanned']}\n"
        f"• NSFW Blocked: {stats['nsfw_blocked']}\n"
        f"• False Positives: {stats['false_positives']}\n"
        f"• User Reports: {stats['user_reports']}"
    )
    
    await sendMessage(message, status_text, btn.build_menu(2))

async def show_strictness_settings(query):
    """Show strictness level selection"""
    user_id = query.from_user.id
    settings = user_data[user_id]['nsfw_filter']
    current_strictness = settings['strictness']
    
    btn = ButtonMaker()
    
    # Create buttons for each strictness level
    for level, description in STRICTNESS_DESCRIPTIONS.items():
        is_current = level == current_strictness
        prefix = "🔘" if is_current else "⚪"
        btn.ibutton(f"{prefix} {description}", f"nsfw_set_strictness_{user_id}_{level}")
    
    btn.ibutton("⬅️ Back", f"nsfw_back_{user_id}")
    
    strictness_text = (
        f"🎚️ <b>NSFW Filter Strictness</b>\n\n"
        f"<b>Current Level:</b> {STRICTNESS_DESCRIPTIONS[current_strictness]}\n\n"
        f"<b>Level Descriptions:</b>\n\n"
        f"<b>Off:</b> No NSFW filtering applied\n"
        f"<b>Low:</b> Only blocks obvious adult sites\n"
        f"<b>Medium:</b> Balanced approach (recommended)\n"
        f"<b>High:</b> Aggressive filtering, may have false positives\n"
        f"<b>Strict:</b> Blocks any content with NSFW indicators\n\n"
        f"<i>Higher levels may block legitimate content. You can report false positives to improve the filter.</i>"
    )
    
    await query.edit_message_text(strictness_text, reply_markup=btn.build_menu(1))

async def show_test_interface(query):
    """Show URL testing interface"""
    user_id = query.from_user.id
    
    btn = ButtonMaker()
    btn.ibutton("⬅️ Back", f"nsfw_back_{user_id}")
    
    test_text = (
        f"🧪 <b>NSFW Filter Testing</b>\n\n"
        f"Send a URL in the next message to test the NSFW filter.\n\n"
        f"The bot will analyze the URL and show:\n"
        f"• Detection results\n"
        f"• Confidence level\n"
        f"• Blocking reasons\n"
        f"• Filter decision\n\n"
        f"<i>This is for testing purposes only. No downloads will be initiated.</i>"
    )
    
    await query.edit_message_text(test_text, reply_markup=btn.build_menu(1))
    
    # Set user in test mode
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['nsfw_test_mode'] = True

async def show_statistics(query):
    """Show detailed NSFW filter statistics"""
    user_id = query.from_user.id
    
    btn = ButtonMaker()
    btn.ibutton("🔄 Refresh", f"nsfw_stats_{user_id}")
    btn.ibutton("📊 Reset Stats", f"nsfw_reset_stats_{user_id}")
    btn.ibutton("⬅️ Back", f"nsfw_back_{user_id}")
    
    stats = nsfw_filter.get_stats()
    
    # Calculate percentages
    total = stats['total_scanned']
    blocked_pct = (stats['nsfw_blocked'] / total * 100) if total > 0 else 0
    false_pos_pct = (stats['false_positives'] / stats['nsfw_blocked'] * 100) if stats['nsfw_blocked'] > 0 else 0
    
    stats_text = (
        f"📊 <b>NSFW Filter Statistics</b>\n\n"
        f"<b>📈 Scanning Activity:</b>\n"
        f"• Total URLs Scanned: {stats['total_scanned']}\n"
        f"• NSFW Content Blocked: {stats['nsfw_blocked']} ({blocked_pct:.1f}%)\n"
        f"• Clean Content Allowed: {total - stats['nsfw_blocked']}\n\n"
        f"<b>🎯 Accuracy Metrics:</b>\n"
        f"• False Positives: {stats['false_positives']} ({false_pos_pct:.1f}%)\n"
        f"• User Reports: {stats['user_reports']}\n\n"
        f"<b>🔧 Filter Performance:</b>\n"
        f"• Cache Size: {len(nsfw_filter.detection_cache)}\n"
        f"• Known NSFW Domains: {len(nsfw_filter.nsfw_domains)}\n"
        f"• NSFW Keywords: {len(nsfw_filter.nsfw_keywords)}\n"
        f"• Safe Domains: {len(nsfw_filter.safe_domains)}\n\n"
        f"<i>Statistics are global across all users.</i>"
    )
    
    await query.edit_message_text(stats_text, reply_markup=btn.build_menu(1))

async def show_help(query):
    """Show NSFW filter help"""
    user_id = query.from_user.id
    
    btn = ButtonMaker()
    btn.ibutton("⬅️ Back", f"nsfw_back_{user_id}")
    
    help_text = (
        f"ℹ️ <b>NSFW Content Filter Help</b>\n\n"
        f"<b>🛡️ What it does:</b>\n"
        f"• Automatically scans URLs for adult/NSFW content\n"
        f"• Blocks downloads from known adult sites\n"
        f"• Analyzes content titles and descriptions\n"
        f"• Protects against unwanted adult content\n\n"
        f"<b>🎚️ Strictness Levels:</b>\n"
        f"• <b>Off:</b> No filtering (not recommended)\n"
        f"• <b>Low:</b> Only obvious adult sites blocked\n"
        f"• <b>Medium:</b> Balanced protection (recommended)\n"
        f"• <b>High:</b> Aggressive filtering\n"
        f"• <b>Strict:</b> Maximum protection\n\n"
        f"<b>🔧 Features:</b>\n"
        f"• <b>Block Downloads:</b> Prevent NSFW downloads\n"
        f"• <b>Show Warnings:</b> Display warning messages\n"
        f"• <b>Allow Override:</b> Let users bypass blocks\n"
        f"• <b>Auto-Delete:</b> Remove NSFW messages\n"
        f"• <b>Reporting:</b> Report false positives\n\n"
        f"<b>🧪 Testing:</b>\n"
        f"Use the test feature to check how URLs are classified.\n\n"
        f"<b>📊 Reporting Issues:</b>\n"
        f"• False Positive: Clean content blocked\n"
        f"• Missed Content: NSFW content not blocked\n\n"
        f"<b>Commands:</b>\n"
        f"• <code>/nsfwfilter</code> - Open settings\n"
        f"• <code>/reportfp [URL]</code> - Report false positive\n"
        f"• <code>/reportmissed [URL]</code> - Report missed content"
    )
    
    await query.edit_message_text(help_text, reply_markup=btn.build_menu(1))

@new_task
async def nsfw_test_handler(_, message: Message):
    """Handle URL testing for NSFW filter"""
    user_id = message.from_user.id
    
    # Check if user is in test mode
    if user_id not in user_data or not user_data[user_id].get('nsfw_test_mode', False):
        return
    
    # Clear test mode
    user_data[user_id]['nsfw_test_mode'] = False
    
    # Extract URL from message
    text = message.text or message.caption or ""
    
    # Simple URL extraction
    import re
    url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')
    urls = url_pattern.findall(text)
    
    if not urls:
        await sendMessage(message, "❌ No URL found in your message. Please send a valid URL.")
        return
    
    url = urls[0]  # Test first URL
    
    # Scan the URL
    try:
        scan_result = await scan_url_for_nsfw(url, text, "")
        
        # Format results
        confidence_bar = "█" * int(scan_result['confidence'] * 10) + "░" * (10 - int(scan_result['confidence'] * 10))
        
        result_text = (
            f"🧪 <b>NSFW Filter Test Results</b>\n\n"
            f"<b>URL:</b> <code>{url[:50]}...</code>\n\n"
            f"<b>🔍 Detection Results:</b>\n"
            f"• NSFW Detected: {'✅ Yes' if scan_result['is_nsfw'] else '❌ No'}\n"
            f"• Confidence: {scan_result['confidence']:.2f} ({confidence_bar})\n"
            f"• Would Block: {'✅ Yes' if scan_result['blocked'] else '❌ No'}\n"
            f"• Safe Override: {'✅ Yes' if scan_result['safe_override'] else '❌ No'}\n\n"
            f"<b>🔍 Detection Reasons:</b>\n"
        )
        
        if scan_result['reasons']:
            for i, reason in enumerate(scan_result['reasons'][:5], 1):
                result_text += f"{i}. {reason}\n"
        else:
            result_text += "• No specific reasons found\n"
        
        result_text += f"\n<i>Test completed. This was for analysis only.</i>"
        
        await sendMessage(message, result_text)
        
    except Exception as e:
        LOGGER.error(f"Error testing URL for NSFW: {str(e)}")
        await sendMessage(message, f"❌ Error testing URL: {str(e)}")

@new_task
async def nsfw_callback_handler(_, query):
    """Handle NSFW settings callbacks"""
    data = query.data.split("_")
    if len(data) < 3:
        return
    
    user_id = query.from_user.id
    action = data[1]
    
    # Extract target user ID
    try:
        target_user = int(data[2]) if len(data) > 2 else user_id
    except ValueError:
        target_user = user_id
    
    if user_id != target_user:
        await query.answer("❌ Not your settings!", show_alert=True)
        return
    
    settings = user_data[user_id]['nsfw_filter']
    
    try:
        if action == "toggle":
            setting_name = data[3] if len(data) > 3 else ""
            if setting_name == "enabled":
                settings['enabled'] = not settings['enabled']
            elif setting_name == "downloads":
                settings['block_downloads'] = not settings['block_downloads']
            elif setting_name == "warnings":
                settings['show_warnings'] = not settings['show_warnings']
            elif setting_name == "override":
                settings['allow_override'] = not settings['allow_override']
            elif setting_name == "reports":
                settings['report_enabled'] = not settings['report_enabled']
            elif setting_name == "delete":
                settings['auto_delete_nsfw'] = not settings['auto_delete_nsfw']
            
            update_user_ldata(user_id, 'nsfw_filter', settings)
            await show_nsfw_settings_edit(query)
        
        elif action == "strictness":
            await show_strictness_settings(query)
        
        elif action == "set" and len(data) > 4:
            if data[3] == "strictness":
                new_level = data[4]
                if new_level in STRICTNESS_DESCRIPTIONS:
                    settings['strictness'] = new_level
                    update_user_ldata(user_id, 'nsfw_filter', settings)
                    await show_strictness_settings(query)
        
        elif action == "test":
            await show_test_interface(query)
        
        elif action == "stats":
            await show_statistics(query)
        
        elif action == "reset" and len(data) > 3 and data[3] == "stats":
            # Reset statistics (admin only or user's own stats)
            nsfw_filter.stats = {
                'total_scanned': 0,
                'nsfw_blocked': 0,
                'false_positives': 0,
                'user_reports': 0
            }
            await show_statistics(query)
        
        elif action == "help":
            await show_help(query)
        
        elif action == "back":
            await show_nsfw_settings_edit(query)
        
        elif action == "close":
            await deleteMessage(query.message)
        
        await query.answer()
        
    except Exception as e:
        LOGGER.error(f"Error in NSFW callback: {str(e)}")
        await query.answer("❌ An error occurred!", show_alert=True)

async def show_nsfw_settings_edit(query):
    """Show NSFW settings (for edit message)"""
    user_id = query.from_user.id
    settings = user_data[user_id]['nsfw_filter']
    
    btn = ButtonMaker()
    
    # Toggle buttons
    enabled_text = "✅ Enabled" if settings['enabled'] else "❌ Disabled"
    downloads_text = "✅ Enabled" if settings['block_downloads'] else "❌ Disabled"
    warnings_text = "✅ Enabled" if settings['show_warnings'] else "❌ Disabled"
    override_text = "✅ Enabled" if settings['allow_override'] else "❌ Disabled"
    reports_text = "✅ Enabled" if settings['report_enabled'] else "❌ Disabled"
    auto_delete_text = "✅ Enabled" if settings['auto_delete_nsfw'] else "❌ Disabled"
    
    strictness_text = STRICTNESS_DESCRIPTIONS[settings['strictness']]
    
    btn.ibutton(f"NSFW Filter: {enabled_text}", f"nsfw_toggle_enabled_{user_id}")
    btn.ibutton(f"Block Downloads: {downloads_text}", f"nsfw_toggle_downloads_{user_id}")
    btn.ibutton(f"Show Warnings: {warnings_text}", f"nsfw_toggle_warnings_{user_id}")
    btn.ibutton(f"Allow Override: {override_text}", f"nsfw_toggle_override_{user_id}")
    
    # Strictness selection
    btn.ibutton("🎚️ Strictness Level", f"nsfw_strictness_{user_id}")
    
    # Advanced options
    btn.ibutton(f"📊 Reporting: {reports_text}", f"nsfw_toggle_reports_{user_id}")
    btn.ibutton(f"🗑️ Auto-Delete: {auto_delete_text}", f"nsfw_toggle_delete_{user_id}")
    btn.ibutton("🏠 Domain Whitelist", f"nsfw_whitelist_{user_id}")
    
    # Testing and stats
    btn.ibutton("🧪 Test URL", f"nsfw_test_{user_id}")
    btn.ibutton("📊 Statistics", f"nsfw_stats_{user_id}")
    btn.ibutton("ℹ️ Help", f"nsfw_help_{user_id}")
    btn.ibutton("❌ Close", f"nsfw_close_{user_id}")
    
    # Build status text
    stats = nsfw_filter.get_stats()
    status_text = (
        f"🛡️ <b>NSFW Content Filter Settings</b>\n\n"
        f"<b>Filter Status:</b> {enabled_text}\n"
        f"<b>Strictness:</b> {strictness_text}\n"
        f"<b>Block Downloads:</b> {downloads_text}\n"
        f"<b>Show Warnings:</b> {warnings_text}\n"
        f"<b>User Override:</b> {override_text}\n"
        f"<b>Reporting:</b> {reports_text}\n"
        f"<b>Auto-Delete:</b> {auto_delete_text}\n\n"
        f"<b>📊 Global Statistics:</b>\n"
        f"• Total Scanned: {stats['total_scanned']}\n"
        f"• NSFW Blocked: {stats['nsfw_blocked']}\n"
        f"• False Positives: {stats['false_positives']}\n"
        f"• User Reports: {stats['user_reports']}"
    )
    
    await query.edit_message_text(status_text, reply_markup=btn.build_menu(2))

# Register command handler
bot.add_handler(MessageHandler(nsfw_settings_cmd, 
                              filters.command("nsfwfilter") & CustomFilters.authorized))

# Register test handler
bot.add_handler(MessageHandler(nsfw_test_handler, 
                              filters.text & CustomFilters.authorized))

# Register callback handler
bot.add_handler(CallbackQueryHandler(nsfw_callback_handler, 
                                   filters.regex(r"^nsfw_")))

LOGGER.info("NSFW Settings module loaded successfully!")