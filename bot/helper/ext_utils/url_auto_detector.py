#!/usr/bin/env python3
"""
URL Auto-Detection and Download System for WZML-X Bot

This module provides automatic detection of supported URLs and initiates downloads
without manual intervention. It supports various URL types including:
- Direct download links
- Torrent/magnet links  
- Cloud storage links (Google Drive, Mega, etc.)
- Video streaming sites
- File hosting services
- And more...
"""

import re
import asyncio
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Optional, Tuple, Union
from functools import lru_cache

from bot import LOGGER, config_dict, user_data
from bot.helper.ext_utils.bot_utils import (
    is_url,
    is_magnet,
    is_mega_link,
    is_gdrive_link,
    is_telegram_link,
    is_share_link,
    is_index_link,
)
from bot.helper.mirror_utils.download_utils.direct_link_generator import direct_link_generator

class URLAutoDetector:
    """
    Comprehensive URL detection and auto-download system
    """
    
    def __init__(self):
        self.supported_domains = self._load_supported_domains()
        self.url_patterns = self._compile_patterns()
        self.detection_cache = {}
        
    def _load_supported_domains(self) -> Dict[str, str]:
        """Load all supported domains categorized by type"""
        return {
            # Video/Streaming sites
            'video': [
                'youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com',
                'twitch.tv', 'facebook.com', 'instagram.com', 'twitter.com',
                'tiktok.com', 'soundcloud.com', 'bandcamp.com'
            ],
            
            # Cloud Storage
            'cloud': [
                'drive.google.com', 'docs.google.com', 'mega.nz', 'mega.co.nz',
                'dropbox.com', 'onedrive.live.com', '1drv.ms', 'box.com',
                'pcloud.com', 'mediafire.com', 'zippyshare.com'
            ],
            
            # File Hosting Services
            'filehost': [
                'anonfiles.com', 'hotfile.io', 'bayfiles.com', 'megaupload.nz',
                'letsupload.cc', 'filechan.org', 'myfile.is', 'vshare.is',
                'rapidshare.nu', 'lolabits.se', 'openload.cc', 'share-online.is',
                'upvid.cc', '1fichier.com', '2shared.com', '4shared.com',
                'alfafile.net', 'anzfile.net', 'clicknupload.cc', 'dailyuploads.net',
                'ddownload.com', 'depositfiles.com', 'desiupload.co', 'drop.download',
                'earn4files.com', 'easybytez.com', 'extmatrix.com', 'fastclick.to',
                'file4go.com', 'filebin.ca', 'filecandy.net', 'filefactory.com',
                'filejoker.net', 'filerio.in', 'filesmonster.com', 'fileup.cc',
                'fshare.vn', 'gofile.io', 'hexupload.net', 'hitfile.net',
                'icerbox.com', 'isra.cloud', 'katfile.com', 'keep2share.cc',
                'littlebyte.net', 'lufi.io', 'mexa.sh', 'mixdrop.co',
                'nitroflare.com', 'nofile.io', 'racaty.net', 'rapidgator.net',
                'rg.to', 'send.cm', 'sendspace.com', 'solidfiles.com',
                'streamtape.com', 'temp.sh', 'turbobit.net', 'uploadbox.io',
                'uploadee.com', 'uploadhaven.com', 'uploading.vn', 'uploadrar.com',
                'usersdrive.com', 'usersfiles.com', 'we.tl', 'wetransfer.com',
                'workupload.com', 'xubster.com', 'yadi.sk', 'disk.yandex.ru'
            ],
            
            # Direct Download Sites
            'direct': [
                'gdtot.me', 'gdtot.pro', 'gdflix.top', 'gdflix.pro',
                'filepress.store', 'filebee.net', 'appdrive.in',
                'driveapp.in', 'drivehub.ws', 'gdrive.vip',
                'hubdrive.in', 'katdrive.net', 'kolop.icu',
                'sharer.pw', 'shrdsk.me', 'drivesharer.in'
            ],
            
            # Torrent/Magnet
            'torrent': [
                'thepiratebay.org', '1337x.to', 'rarbg.to', 'torrentz2.eu',
                'kickasstorrents.to', 'limetorrents.info', 'torlock.com',
                'nyaa.si', 'eztv.re', 'yts.mx', 'magnetdl.com'
            ],
            
            # Archive/Compressed files
            'archive': [
                'archive.org', 'web.archive.org'
            ],
            
            # Telegram
            'telegram': [
                't.me', 'telegram.me', 'telegram.dog', 'telegram.space'
            ]
        }
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for different URL types"""
        return {
            'magnet': re.compile(r'magnet:\?xt=urn:(btih|btmh):[a-zA-Z0-9]{20,40}', re.IGNORECASE),
            'torrent_file': re.compile(r'.*\.torrent$', re.IGNORECASE),
            'gdrive': re.compile(r'https?://drive\.google\.com/.*', re.IGNORECASE),
            'gdrive_folder': re.compile(r'https?://drive\.google\.com/drive/folders/([a-zA-Z0-9-_]+)', re.IGNORECASE),
            'gdrive_file': re.compile(r'https?://drive\.google\.com/file/d/([a-zA-Z0-9-_]+)', re.IGNORECASE),
            'mega': re.compile(r'https?://mega\.(nz|co\.nz)/', re.IGNORECASE),
            'youtube': re.compile(r'https?://(www\.)?(youtube\.com|youtu\.be)/', re.IGNORECASE),
            'telegram': re.compile(r'https?://(t\.me|telegram\.(me|dog|space))/', re.IGNORECASE),
            'http_url': re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE),
            'ftp_url': re.compile(r'ftp://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE),
        }
    
    @lru_cache(maxsize=1000)
    def detect_url_type(self, url: str) -> Tuple[str, Dict[str, Union[str, bool]]]:
        """
        Detect the type of URL and return metadata
        
        Args:
            url: The URL to analyze
            
        Returns:
            Tuple of (url_type, metadata_dict)
        """
        if not url or not isinstance(url, str):
            return 'invalid', {}
            
        url = url.strip()
        metadata = {
            'url': url,
            'domain': '',
            'downloadable': False,
            'requires_auth': False,
            'supports_batch': False,
            'estimated_type': 'unknown'
        }
        
        # Extract domain
        try:
            parsed = urlparse(url)
            metadata['domain'] = parsed.netloc.lower()
        except Exception:
            return 'invalid', metadata
        
        # Check magnet links first
        if self.url_patterns['magnet'].match(url):
            metadata.update({
                'downloadable': True,
                'estimated_type': 'torrent',
                'supports_batch': False
            })
            return 'magnet', metadata
        
        # Check torrent files
        if self.url_patterns['torrent_file'].match(url):
            metadata.update({
                'downloadable': True,
                'estimated_type': 'torrent',
                'supports_batch': False
            })
            return 'torrent_file', metadata
        
        # Check Google Drive
        if self.url_patterns['gdrive'].match(url):
            if self.url_patterns['gdrive_folder'].match(url):
                metadata.update({
                    'downloadable': True,
                    'estimated_type': 'cloud_folder',
                    'supports_batch': True
                })
                return 'gdrive_folder', metadata
            elif self.url_patterns['gdrive_file'].match(url):
                metadata.update({
                    'downloadable': True,
                    'estimated_type': 'cloud_file',
                    'supports_batch': False
                })
                return 'gdrive_file', metadata
            else:
                metadata.update({
                    'downloadable': True,
                    'estimated_type': 'cloud',
                    'supports_batch': False
                })
                return 'gdrive', metadata
        
        # Check Mega
        if self.url_patterns['mega'].match(url):
            metadata.update({
                'downloadable': True,
                'estimated_type': 'cloud',
                'supports_batch': url.find('#F!') != -1  # Folder link
            })
            return 'mega', metadata
        
        # Check Telegram
        if self.url_patterns['telegram'].match(url):
            metadata.update({
                'downloadable': True,
                'estimated_type': 'telegram',
                'supports_batch': False,
                'requires_auth': True
            })
            return 'telegram', metadata
        
        # Check YouTube and video sites
        if self.url_patterns['youtube'].match(url):
            metadata.update({
                'downloadable': True,
                'estimated_type': 'video',
                'supports_batch': 'playlist' in url or 'channel' in url
            })
            return 'youtube', metadata
        
        # Check against domain lists
        domain = metadata['domain']
        for category, domains in self.supported_domains.items():
            if any(d in domain for d in domains):
                metadata.update({
                    'downloadable': True,
                    'estimated_type': category,
                    'supports_batch': category in ['video', 'cloud']
                })
                return category, metadata
        
        # Check if it's a general HTTP/HTTPS URL
        if self.url_patterns['http_url'].match(url):
            metadata.update({
                'downloadable': True,
                'estimated_type': 'http',
                'supports_batch': False
            })
            return 'http', metadata
        
        # Check FTP
        if self.url_patterns['ftp_url'].match(url):
            metadata.update({
                'downloadable': True,
                'estimated_type': 'ftp',
                'supports_batch': False
            })
            return 'ftp', metadata
        
        return 'unknown', metadata
    
    def extract_urls_from_text(self, text: str) -> List[Tuple[str, Dict]]:
        """
        Extract all URLs from text and detect their types
        
        Args:
            text: Text to search for URLs
            
        Returns:
            List of tuples (url, metadata)
        """
        if not text:
            return []
        
        urls = []
        
        # Find all HTTP/HTTPS URLs
        http_urls = self.url_patterns['http_url'].findall(text)
        for url in http_urls:
            url_type, metadata = self.detect_url_type(url)
            if metadata['downloadable']:
                urls.append((url, metadata))
        
        # Find magnet links
        magnet_urls = self.url_patterns['magnet'].findall(text)
        for match in magnet_urls:
            # Reconstruct full magnet URL
            magnet_start = text.find('magnet:')
            if magnet_start != -1:
                magnet_end = text.find(' ', magnet_start)
                if magnet_end == -1:
                    magnet_end = len(text)
                magnet_url = text[magnet_start:magnet_end]
                url_type, metadata = self.detect_url_type(magnet_url)
                urls.append((magnet_url, metadata))
        
        return urls
    
    def is_auto_downloadable(self, url: str, user_id: int = None) -> bool:
        """
        Check if URL should be auto-downloaded based on user preferences
        
        Args:
            url: URL to check
            user_id: User ID for preference checking
            
        Returns:
            Boolean indicating if auto-download should proceed
        """
        url_type, metadata = self.detect_url_type(url)
        
        if not metadata['downloadable']:
            return False
        
        # Check user preferences if available
        if user_id and user_id in user_data:
            user_prefs = user_data[user_id].get('auto_download', {})
            
            # Check if auto-download is enabled for this user
            if not user_prefs.get('enabled', False):
                return False
            
            # Check specific type preferences
            allowed_types = user_prefs.get('allowed_types', ['all'])
            if 'all' not in allowed_types and url_type not in allowed_types:
                return False
            
            # Check domain whitelist/blacklist
            domain = metadata['domain']
            whitelist = user_prefs.get('domain_whitelist', [])
            blacklist = user_prefs.get('domain_blacklist', [])
            
            if whitelist and not any(d in domain for d in whitelist):
                return False
            
            if blacklist and any(d in domain for d in blacklist):
                return False
        
        # Default behavior - auto-download safe types
        safe_types = ['gdrive', 'mega', 'torrent_file', 'magnet', 'youtube']
        return url_type in safe_types
    
    def get_download_priority(self, url: str) -> int:
        """
        Get download priority for URL (higher number = higher priority)
        
        Args:
            url: URL to prioritize
            
        Returns:
            Priority score (0-100)
        """
        url_type, metadata = self.detect_url_type(url)
        
        priority_map = {
            'magnet': 90,
            'torrent_file': 85,
            'gdrive_file': 80,
            'gdrive_folder': 75,
            'mega': 70,
            'youtube': 65,
            'telegram': 60,
            'filehost': 50,
            'direct': 45,
            'cloud': 40,
            'video': 35,
            'http': 20,
            'ftp': 15,
        }
        
        base_priority = priority_map.get(url_type, 10)
        
        # Boost priority for certain domains
        domain = metadata['domain']
        if any(trusted in domain for trusted in ['drive.google.com', 'mega.nz', 'youtube.com']):
            base_priority += 10
        
        return min(base_priority, 100)
    
    async def process_auto_download(self, url: str, message, **kwargs) -> bool:
        """
        Process automatic download for detected URL
        
        Args:
            url: URL to download
            message: Telegram message object
            **kwargs: Additional parameters for download
            
        Returns:
            Boolean indicating success
        """
        try:
            from bot.modules.mirror_leech import _mirror_leech
            
            # Create a modified message with the URL
            modified_message = message
            modified_message.text = f"/mirror {url}"
            
            # Process the download
            await _mirror_leech(message.client, modified_message, **kwargs)
            
            LOGGER.info(f"Auto-download initiated for URL: {url}")
            return True
            
        except Exception as e:
            LOGGER.error(f"Auto-download failed for URL {url}: {str(e)}")
            return False

# Global instance
url_detector = URLAutoDetector()

# Convenience functions
def detect_urls_in_message(text: str) -> List[Tuple[str, Dict]]:
    """Extract and detect URLs from message text"""
    return url_detector.extract_urls_from_text(text)

def is_supported_url(url: str) -> bool:
    """Check if URL is supported for download"""
    _, metadata = url_detector.detect_url_type(url)
    return metadata['downloadable']

def should_auto_download(url: str, user_id: int = None) -> bool:
    """Check if URL should be auto-downloaded"""
    return url_detector.is_auto_downloadable(url, user_id)

def get_url_info(url: str) -> Dict:
    """Get comprehensive information about a URL"""
    url_type, metadata = url_detector.detect_url_type(url)
    metadata['type'] = url_type
    metadata['priority'] = url_detector.get_download_priority(url)
    return metadata