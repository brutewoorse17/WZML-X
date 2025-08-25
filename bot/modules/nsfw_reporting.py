#!/usr/bin/env python3
"""
NSFW Filter Reporting Module

This module handles user reporting of false positives and missed NSFW content
to improve the filter accuracy over time.
"""

from pyrogram import filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
import re

from bot import bot, LOGGER, user_data
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.nsfw_filter import (
    nsfw_filter,
    report_false_positive,
    report_missed_content,
    scan_url_for_nsfw
)

@new_task
async def report_false_positive_cmd(_, message: Message):
    """Handle /reportfp command for false positive reporting"""
    user_id = message.from_user.id
    
    # Extract URL from command
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        help_text = (
            f"📝 <b>Report False Positive</b>\n\n"
            f"<b>Usage:</b> <code>/reportfp [URL]</code>\n\n"
            f"<b>Example:</b>\n"
            f"<code>/reportfp https://example.com/safe-content</code>\n\n"
            f"<i>Use this command to report URLs that were incorrectly blocked as NSFW content.</i>"
        )
        await sendMessage(message, help_text)
        return
    
    url = args[1].strip()
    
    # Validate URL format
    url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')
    if not url_pattern.match(url):
        await sendMessage(message, "❌ Invalid URL format. Please provide a valid HTTP/HTTPS URL.")
        return
    
    try:
        # Scan the URL to get current classification
        scan_result = await scan_url_for_nsfw(url, "", "")
        
        # Report false positive
        report_false_positive(url, user_id)
        
        # Create response
        confidence = scan_result['confidence']
        blocked = scan_result['blocked']
        
        response_text = (
            f"📝 <b>False Positive Reported</b>\n\n"
            f"<b>URL:</b> <code>{url[:50]}{'...' if len(url) > 50 else ''}</code>\n"
            f"<b>Current Classification:</b> {'🚫 Blocked' if blocked else '✅ Allowed'}\n"
            f"<b>Confidence:</b> {confidence:.0%}\n\n"
            f"<b>Status:</b> ✅ Report submitted successfully\n\n"
            f"<i>Thank you for helping improve the NSFW filter! "
            f"Your report will be reviewed and may improve future classifications.</i>"
        )
        
        await sendMessage(message, response_text)
        
        # Log the report
        LOGGER.info(f"False positive reported by user {user_id}: {url} (confidence: {confidence:.2f})")
        
    except Exception as e:
        LOGGER.error(f"Error processing false positive report: {str(e)}")
        await sendMessage(message, f"❌ Error processing report: {str(e)}")

@new_task
async def report_missed_content_cmd(_, message: Message):
    """Handle /reportmissed command for missed NSFW content reporting"""
    user_id = message.from_user.id
    
    # Extract URL from command
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        help_text = (
            f"📝 <b>Report Missed NSFW Content</b>\n\n"
            f"<b>Usage:</b> <code>/reportmissed [URL]</code>\n\n"
            f"<b>Example:</b>\n"
            f"<code>/reportmissed https://example.com/adult-content</code>\n\n"
            f"<i>Use this command to report URLs containing NSFW content that were not blocked by the filter.</i>\n\n"
            f"<b>⚠️ Warning:</b> Only report URLs that actually contain adult/NSFW content."
        )
        await sendMessage(message, help_text)
        return
    
    url = args[1].strip()
    
    # Validate URL format
    url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')
    if not url_pattern.match(url):
        await sendMessage(message, "❌ Invalid URL format. Please provide a valid HTTP/HTTPS URL.")
        return
    
    try:
        # Scan the URL to get current classification
        scan_result = await scan_url_for_nsfw(url, "", "")
        
        # Report missed content
        report_missed_content(url, user_id)
        
        # Create response
        confidence = scan_result['confidence']
        blocked = scan_result['blocked']
        
        response_text = (
            f"📝 <b>Missed NSFW Content Reported</b>\n\n"
            f"<b>URL:</b> <code>{url[:50]}{'...' if len(url) > 50 else ''}</code>\n"
            f"<b>Current Classification:</b> {'🚫 Blocked' if blocked else '✅ Allowed'}\n"
            f"<b>Confidence:</b> {confidence:.0%}\n\n"
            f"<b>Status:</b> ✅ Report submitted successfully\n\n"
            f"<i>Thank you for helping improve the NSFW filter! "
            f"This URL will be reviewed and may be added to the block list.</i>"
        )
        
        await sendMessage(message, response_text)
        
        # Log the report
        LOGGER.info(f"Missed NSFW content reported by user {user_id}: {url} (confidence: {confidence:.2f})")
        
    except Exception as e:
        LOGGER.error(f"Error processing missed content report: {str(e)}")
        await sendMessage(message, f"❌ Error processing report: {str(e)}")

@new_task
async def nsfw_stats_cmd(_, message: Message):
    """Handle /nsfwstats command for viewing NSFW filter statistics"""
    try:
        stats = nsfw_filter.get_stats()
        
        # Calculate percentages
        total = stats['total_scanned']
        blocked_pct = (stats['nsfw_blocked'] / total * 100) if total > 0 else 0
        false_pos_pct = (stats['false_positives'] / stats['nsfw_blocked'] * 100) if stats['nsfw_blocked'] > 0 else 0
        
        stats_text = (
            f"📊 <b>NSFW Filter Statistics</b>\n\n"
            f"<b>📈 Scanning Activity:</b>\n"
            f"• Total URLs Scanned: {stats['total_scanned']:,}\n"
            f"• NSFW Content Blocked: {stats['nsfw_blocked']:,} ({blocked_pct:.1f}%)\n"
            f"• Clean Content Allowed: {total - stats['nsfw_blocked']:,}\n\n"
            f"<b>🎯 Accuracy Metrics:</b>\n"
            f"• False Positives Reported: {stats['false_positives']:,} ({false_pos_pct:.1f}%)\n"
            f"• Total User Reports: {stats['user_reports']:,}\n\n"
            f"<b>🔧 Filter Database:</b>\n"
            f"• Known NSFW Domains: {len(nsfw_filter.nsfw_domains):,}\n"
            f"• NSFW Keywords: {len(nsfw_filter.nsfw_keywords):,}\n"
            f"• Safe Domains: {len(nsfw_filter.safe_domains):,}\n"
            f"• Detection Cache Size: {len(nsfw_filter.detection_cache):,}\n\n"
            f"<i>Statistics are global across all bot users.</i>\n\n"
            f"<b>Commands:</b>\n"
            f"• <code>/nsfwfilter</code> - Configure settings\n"
            f"• <code>/reportfp [URL]</code> - Report false positive\n"
            f"• <code>/reportmissed [URL]</code> - Report missed content"
        )
        
        await sendMessage(message, stats_text)
        
    except Exception as e:
        LOGGER.error(f"Error getting NSFW stats: {str(e)}")
        await sendMessage(message, f"❌ Error getting statistics: {str(e)}")

@new_task
async def nsfw_test_cmd(_, message: Message):
    """Handle /nsfwtest command for testing URL classification"""
    user_id = message.from_user.id
    
    # Extract URL from command
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        help_text = (
            f"🧪 <b>NSFW Filter Test</b>\n\n"
            f"<b>Usage:</b> <code>/nsfwtest [URL]</code>\n\n"
            f"<b>Example:</b>\n"
            f"<code>/nsfwtest https://example.com/content</code>\n\n"
            f"<i>This command tests how the NSFW filter classifies a URL without downloading anything.</i>"
        )
        await sendMessage(message, help_text)
        return
    
    url = args[1].strip()
    
    # Validate URL format
    url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')
    if not url_pattern.match(url):
        await sendMessage(message, "❌ Invalid URL format. Please provide a valid HTTP/HTTPS URL.")
        return
    
    try:
        # Scan the URL
        scan_result = await scan_url_for_nsfw(url, "", "")
        
        # Get user-specific blocking decision
        from bot.modules.nsfw_integration import nsfw_integration
        would_block = nsfw_integration.nsfw_filter.is_content_blocked(user_id, scan_result)
        
        # Format confidence as progress bar
        confidence = scan_result['confidence']
        confidence_bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
        
        # Extract domain
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        
        result_text = (
            f"🧪 <b>NSFW Filter Test Results</b>\n\n"
            f"<b>URL:</b> <code>{url[:60]}{'...' if len(url) > 60 else ''}</code>\n"
            f"<b>Domain:</b> <code>{domain}</code>\n\n"
            f"<b>🔍 Detection Results:</b>\n"
            f"• NSFW Detected: {'✅ Yes' if scan_result['is_nsfw'] else '❌ No'}\n"
            f"• Confidence: {confidence:.0%} {confidence_bar}\n"
            f"• Would Block (You): {'🚫 Yes' if would_block else '✅ No'}\n"
            f"• Safe Override: {'✅ Active' if scan_result['safe_override'] else '❌ None'}\n\n"
        )
        
        if scan_result['reasons']:
            result_text += f"<b>🔍 Detection Reasons:</b>\n"
            for i, reason in enumerate(scan_result['reasons'][:5], 1):
                result_text += f"{i}. {reason}\n"
            if len(scan_result['reasons']) > 5:
                result_text += f"... and {len(scan_result['reasons']) - 5} more reasons\n"
        else:
            result_text += f"<b>🔍 Detection Reasons:</b>\nNo specific NSFW indicators found\n"
        
        result_text += (
            f"\n<i>This is a test only - no download was initiated.</i>\n\n"
            f"<b>💡 Tips:</b>\n"
            f"• Adjust your filter strictness in /nsfwfilter settings\n"
            f"• Report false positives with /reportfp\n"
            f"• Report missed content with /reportmissed"
        )
        
        await sendMessage(message, result_text)
        
    except Exception as e:
        LOGGER.error(f"Error testing URL for NSFW: {str(e)}")
        await sendMessage(message, f"❌ Error testing URL: {str(e)}")

# Register command handlers
bot.add_handler(MessageHandler(report_false_positive_cmd, 
                              filters.command("reportfp") & CustomFilters.authorized))

bot.add_handler(MessageHandler(report_missed_content_cmd, 
                              filters.command("reportmissed") & CustomFilters.authorized))

bot.add_handler(MessageHandler(nsfw_stats_cmd, 
                              filters.command("nsfwstats") & CustomFilters.authorized))

bot.add_handler(MessageHandler(nsfw_test_cmd, 
                              filters.command("nsfwtest") & CustomFilters.authorized))

LOGGER.info("NSFW Reporting module loaded successfully!")