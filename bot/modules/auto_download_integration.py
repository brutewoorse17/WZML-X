#!/usr/bin/env python3
"""
Auto-Download Integration Module

This module integrates the auto-download functionality with the existing
mirror/leech system and ensures proper initialization and error handling.
"""

import asyncio
from typing import Dict, Any

from bot import LOGGER, bot_loop
from bot.helper.ext_utils.url_auto_detector import url_detector
from bot.modules.mirror_leech import _mirror_leech

class AutoDownloadIntegration:
    """Integration layer for auto-download functionality"""
    
    def __init__(self):
        self.download_queue = asyncio.Queue()
        self.processing = False
        self.stats = {
            'total_detected': 0,
            'auto_downloaded': 0,
            'user_prompted': 0,
            'failed': 0
        }
    
    async def initialize(self):
        """Initialize the auto-download system"""
        try:
            LOGGER.info("Initializing Auto-Download system...")
            
            # Start the download processor
            if not self.processing:
                asyncio.create_task(self._process_download_queue())
                self.processing = True
            
            LOGGER.info("✅ Auto-Download system initialized successfully")
            
        except Exception as e:
            LOGGER.error(f"❌ Failed to initialize Auto-Download system: {str(e)}")
    
    async def _process_download_queue(self):
        """Process queued downloads"""
        while True:
            try:
                # Get download task from queue
                download_task = await self.download_queue.get()
                
                # Process the download
                await self._execute_download(download_task)
                
                # Mark task as done
                self.download_queue.task_done()
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(1)
                
            except Exception as e:
                LOGGER.error(f"Error processing download queue: {str(e)}")
                await asyncio.sleep(5)
    
    async def _execute_download(self, task: Dict[str, Any]):
        """Execute a single download task"""
        try:
            url = task['url']
            message = task['message']
            options = task.get('options', {})
            
            LOGGER.info(f"Executing auto-download for: {url}")
            
            # Create modified message for mirror/leech
            modified_message = message
            
            # Build command based on options
            cmd_parts = ["/mirror"]  # Default to mirror
            
            if options.get('isLeech', False):
                cmd_parts[0] = "/leech"
            
            if options.get('extract', False):
                cmd_parts.append("-e")
            
            if options.get('compress', False):
                cmd_parts.append("-z")
            
            if options.get('name'):
                cmd_parts.extend(["-n", options['name']])
            
            # Add URL
            cmd_parts.append(url)
            
            # Set the command text
            modified_message.text = " ".join(cmd_parts)
            
            # Execute the download
            await _mirror_leech(
                message.client, 
                modified_message,
                isQbit=options.get('isQbit', False),
                isLeech=options.get('isLeech', False)
            )
            
            self.stats['auto_downloaded'] += 1
            LOGGER.info(f"✅ Auto-download completed for: {url}")
            
        except Exception as e:
            self.stats['failed'] += 1
            LOGGER.error(f"❌ Auto-download failed for {task['url']}: {str(e)}")
    
    async def queue_download(self, url: str, message, **options):
        """Queue a download for processing"""
        try:
            download_task = {
                'url': url,
                'message': message,
                'options': options,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            await self.download_queue.put(download_task)
            LOGGER.info(f"Queued auto-download for: {url}")
            
        except Exception as e:
            LOGGER.error(f"Failed to queue download for {url}: {str(e)}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get auto-download statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'total_detected': 0,
            'auto_downloaded': 0,
            'user_prompted': 0,
            'failed': 0
        }

# Global integration instance
auto_download_integration = AutoDownloadIntegration()

# Enhanced URL detector process_auto_download method
async def enhanced_process_auto_download(url: str, message, **kwargs) -> bool:
    """
    Enhanced auto-download processing with queue management
    """
    try:
        # Queue the download instead of processing immediately
        await auto_download_integration.queue_download(url, message, **kwargs)
        return True
        
    except Exception as e:
        LOGGER.error(f"Enhanced auto-download failed for URL {url}: {str(e)}")
        return False

# Monkey patch the url_detector to use enhanced processing
url_detector.process_auto_download = enhanced_process_auto_download

# Initialize on import
async def init_auto_download_system():
    """Initialize the auto-download system"""
    await auto_download_integration.initialize()

# Schedule initialization
if bot_loop and bot_loop.is_running():
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(init_auto_download_system())
    except RuntimeError:
        asyncio.run(init_auto_download_system())

LOGGER.info("Auto-Download Integration module loaded successfully!")