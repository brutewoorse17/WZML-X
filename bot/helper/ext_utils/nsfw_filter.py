#!/usr/bin/env python3
"""
NSFW Content Filter for WZML-X Bot

This module provides comprehensive NSFW/pornography content detection and blocking
to maintain appropriate usage and protect users from unwanted adult content.
"""

import re
import asyncio
from typing import Dict, List, Tuple, Optional, Set
from urllib.parse import urlparse, unquote
from functools import lru_cache
import hashlib

from bot import LOGGER, config_dict, user_data
from bot.helper.ext_utils.db_handler import DbManger

class NSFWContentFilter:
    """
    Comprehensive NSFW content detection and filtering system
    """
    
    def __init__(self):
        self.nsfw_domains = self._load_nsfw_domains()
        self.nsfw_keywords = self._load_nsfw_keywords()
        self.safe_domains = self._load_safe_domains()
        self.keyword_patterns = self._compile_keyword_patterns()
        self.detection_cache = {}
        self.stats = {
            'total_scanned': 0,
            'nsfw_blocked': 0,
            'false_positives': 0,
            'user_reports': 0
        }
    
    def _load_nsfw_domains(self) -> Set[str]:
        """Load comprehensive list of known NSFW domains"""
        return {
            # Major adult sites
            'pornhub.com', 'xvideos.com', 'xnxx.com', 'redtube.com',
            'youporn.com', 'tube8.com', 'spankbang.com', 'xhamster.com',
            'beeg.com', 'porn.com', 'sex.com', 'xxx.com', 'adult.com',
            'brazzers.com', 'realitykings.com', 'bangbros.com',
            'naughtyamerica.com', 'digitalplayground.com', 'vivid.com',
            
            # OnlyFans and similar platforms
            'onlyfans.com', 'fansly.com', 'justforfans.com', 'loyalfans.com',
            'manyvideos.com', 'clips4sale.com', 'iwantclips.com',
            'adultwork.com', 'streamate.com', 'chaturbate.com',
            'cam4.com', 'livejasmin.com', 'bongacams.com',
            
            # Adult file sharing
            'pornbb.org', 'empornium.me', 'pornolab.net', 'cheggit.me',
            'pornleech.com', 'adultdvdtalk.com', 'vintage-erotica-forum.com',
            
            # Adult torrents
            'empornium.sx', 'pornbay.org', 'sexuria.org', 'cheggit.me',
            'pornleech.com', 'empornium.is', 'oppaitime.com',
            
            # Adult forums and communities  
            'reddit.com/r/nsfw', 'reddit.com/r/porn', 'reddit.com/r/sex',
            'reddit.com/r/gonewild', 'reddit.com/r/realgirls',
            '4chan.org/b/', '4chan.org/s/', '4chan.org/hc/',
            
            # Image hosting with adult content
            'imagefap.com', 'motherless.com', 'heavy-r.com',
            'erome.com', 'sexiezpix.com', 'nude-gals.com',
            
            # Adult manga/hentai
            'nhentai.net', 'hanime.tv', 'hentaihaven.org', 'fakku.net',
            'tsumino.com', 'hitomi.la', 'e-hentai.org', 'exhentai.org',
            'gelbooru.com', 'rule34.xxx', 'danbooru.donmai.us',
            
            # Adult games
            'f95zone.to', 'lewdgames.net', 'adultgameson.com',
            'nutaku.net', 'kimochi.info', 'vndb.org',
            
            # Dating/hookup sites
            'tinder.com', 'adultfriendfinder.com', 'ashley-madison.com',
            'seeking.com', 'benaughty.com', 'flirt.com',
            
            # Adult stores/shops
            'adameve.com', 'lovehoney.com', 'spencers.com',
            'pinkcherry.com', 'extremerestraints.com',
            
            # Cam sites
            'myfreecams.com', 'camsoda.com', 'stripchat.com',
            'xlovecam.com', 'flirt4free.com', 'imlive.com',
            
            # Adult social networks
            'fetlife.com', 'adultspace.com', 'sexsearch.com',
            'alt.com', 'kink.com', 'adultfriendfinder.com',
            
            # Additional domains
            'eporner.com', 'tnaflix.com', 'drtuber.com', 'sunporno.com',
            'nuvid.com', 'porntube.com', 'xtube.com', 'slutload.com',
            'empflix.com', 'keezmovies.com', 'pornoxo.com', 'fapdu.com',
            'zbporn.com', 'upornia.com', 'porndig.com', 'yespornplease.com',
            'porntrex.com', 'hqporner.com', 'pornone.com', 'sexvid.xxx'
        }
    
    def _load_nsfw_keywords(self) -> Set[str]:
        """Load NSFW keywords for content detection"""
        return {
            # Explicit terms
            'porn', 'sex', 'xxx', 'adult', 'nude', 'naked', 'nsfw',
            'erotic', 'sexy', 'horny', 'kinky', 'fetish', 'bdsm',
            
            # Body parts (explicit)
            'boobs', 'tits', 'ass', 'pussy', 'dick', 'cock', 'penis',
            'vagina', 'breast', 'nipple', 'genital',
            
            # Activities
            'masturbat', 'orgasm', 'climax', 'ejaculat', 'cumshot',
            'blowjob', 'handjob', 'footjob', 'rimjob', 'anal',
            'oral', 'threesome', 'gangbang', 'orgy', 'swingers',
            
            # Genres
            'milf', 'teen', 'mature', 'amateur', 'professional',
            'lesbian', 'gay', 'bisexual', 'transgender', 'shemale',
            'bbw', 'ebony', 'asian', 'latina', 'redhead', 'blonde',
            
            # Platforms/sites
            'onlyfans', 'pornhub', 'xvideos', 'chaturbate', 'cam4',
            'livejasmin', 'streamate', 'myfreecams', 'camsoda',
            
            # File types often associated with adult content
            'nude.jpg', 'sex.mp4', 'porn.avi', 'xxx.mkv',
            
            # Common adult content indicators
            '18+', '21+', 'adults only', 'mature content', 'explicit',
            'uncensored', 'hardcore', 'softcore', 'erotica',
            
            # Hentai/anime adult content
            'hentai', 'ecchi', 'doujin', 'ahegao', 'oppai', 'loli',
            'shota', 'futanari', 'yaoi', 'yuri', 'netorare', 'ntr'
        }
    
    def _load_safe_domains(self) -> Set[str]:
        """Load domains that are definitely safe (whitelist)"""
        return {
            # Major platforms
            'youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com',
            'twitch.tv', 'facebook.com', 'instagram.com', 'twitter.com',
            'tiktok.com', 'linkedin.com', 'pinterest.com', 'snapchat.com',
            
            # Cloud storage
            'drive.google.com', 'docs.google.com', 'dropbox.com',
            'onedrive.live.com', 'box.com', 'pcloud.com',
            'mega.nz', 'mega.co.nz', 'mediafire.com',
            
            # File sharing (general)
            'github.com', 'gitlab.com', 'bitbucket.org', 'sourceforge.net',
            'archive.org', 'internet-archive.org',
            
            # Educational/News
            'wikipedia.org', 'britannica.com', 'coursera.org',
            'edx.org', 'khanacademy.org', 'ted.com',
            'bbc.com', 'cnn.com', 'reuters.com', 'ap.org',
            
            # Entertainment (safe)
            'netflix.com', 'disney.com', 'hulu.com', 'amazon.com',
            'spotify.com', 'soundcloud.com', 'bandcamp.com',
            
            # Technology
            'stackoverflow.com', 'stackexchange.com', 'reddit.com',
            'discord.com', 'slack.com', 'zoom.us', 'teams.microsoft.com'
        }
    
    def _compile_keyword_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for keyword detection"""
        patterns = []
        
        # Create patterns for each keyword with word boundaries
        for keyword in self.nsfw_keywords:
            # Case insensitive pattern with word boundaries
            pattern = re.compile(rf'\b{re.escape(keyword)}\b', re.IGNORECASE)
            patterns.append(pattern)
        
        # Additional patterns for common obfuscations
        obfuscation_patterns = [
            re.compile(r'p[0o]rn', re.IGNORECASE),  # p0rn, porn
            re.compile(r's[3e]x', re.IGNORECASE),   # s3x, sex
            re.compile(r'xxx+', re.IGNORECASE),     # xxx, xxxx, etc.
            re.compile(r'n[5s]fw', re.IGNORECASE),  # n5fw, nsfw
            re.compile(r'[0o]nlyfans?', re.IGNORECASE),  # 0nlyfans, onlyfans
        ]
        
        patterns.extend(obfuscation_patterns)
        return patterns
    
    @lru_cache(maxsize=2000)
    def is_nsfw_domain(self, url: str) -> Tuple[bool, str]:
        """
        Check if a domain is known to host NSFW content
        
        Args:
            url: URL to check
            
        Returns:
            Tuple of (is_nsfw, reason)
        """
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc
            
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check exact domain match
            if domain in self.nsfw_domains:
                return True, f"Known NSFW domain: {domain}"
            
            # Check subdomain matches
            for nsfw_domain in self.nsfw_domains:
                if domain.endswith(f'.{nsfw_domain}') or domain == nsfw_domain:
                    return True, f"NSFW subdomain of: {nsfw_domain}"
            
            # Check if it's a known safe domain
            if domain in self.safe_domains:
                return False, f"Known safe domain: {domain}"
            
            # Check for suspicious patterns in domain
            suspicious_patterns = [
                r'porn', r'xxx', r'sex', r'adult', r'nude', r'cam',
                r'live.*sex', r'free.*porn', r'hot.*girls'
            ]
            
            for pattern in suspicious_patterns:
                if re.search(pattern, domain, re.IGNORECASE):
                    return True, f"Suspicious domain pattern: {pattern}"
            
            return False, "Domain not in NSFW database"
            
        except Exception as e:
            LOGGER.error(f"Error checking domain for NSFW: {str(e)}")
            return False, "Error parsing domain"
    
    def detect_nsfw_keywords(self, text: str) -> Tuple[bool, List[str]]:
        """
        Detect NSFW keywords in text content
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (has_nsfw, found_keywords)
        """
        if not text:
            return False, []
        
        text_lower = text.lower()
        found_keywords = []
        
        # Check against compiled patterns
        for pattern in self.keyword_patterns:
            matches = pattern.findall(text_lower)
            if matches:
                found_keywords.extend(matches)
        
        # Additional context-based detection
        nsfw_contexts = [
            # File extensions with adult indicators
            r'\.(?:jpg|jpeg|png|gif|mp4|avi|mkv|mov).*(?:nude|sex|porn|xxx)',
            # Common adult content naming patterns
            r'(?:barely|teen|young).*(?:legal|18)',
            r'(?:hot|sexy|nude).*(?:girls?|women|babes?)',
            r'(?:amateur|homemade).*(?:sex|porn)',
        ]
        
        for context_pattern in nsfw_contexts:
            if re.search(context_pattern, text_lower):
                found_keywords.append("contextual_nsfw_pattern")
                break
        
        return len(found_keywords) > 0, found_keywords
    
    def analyze_url_path(self, url: str) -> Tuple[bool, str]:
        """
        Analyze URL path and parameters for NSFW indicators
        
        Args:
            url: URL to analyze
            
        Returns:
            Tuple of (is_nsfw, reason)
        """
        try:
            parsed = urlparse(url.lower())
            full_path = unquote(parsed.path + parsed.query + parsed.fragment)
            
            # Check for explicit path indicators
            nsfw_path_patterns = [
                r'/(?:porn|sex|xxx|adult|nude|nsfw)/',
                r'/(?:category|tag)/.*(?:porn|sex|xxx|adult)',
                r'/(?:watch|video|stream)/.*(?:sex|porn|xxx)',
                r'\.(?:jpg|jpeg|png|gif|mp4|avi).*(?:nude|sex|porn)',
            ]
            
            for pattern in nsfw_path_patterns:
                if re.search(pattern, full_path):
                    return True, f"NSFW path pattern: {pattern}"
            
            # Check for NSFW keywords in path
            has_nsfw, keywords = self.detect_nsfw_keywords(full_path)
            if has_nsfw:
                return True, f"NSFW keywords in path: {keywords[:3]}"
            
            return False, "Path appears clean"
            
        except Exception as e:
            LOGGER.error(f"Error analyzing URL path: {str(e)}")
            return False, "Error parsing URL path"
    
    async def scan_content(self, url: str, title: str = "", description: str = "") -> Dict:
        """
        Comprehensive NSFW content scanning
        
        Args:
            url: URL to scan
            title: Content title (optional)
            description: Content description (optional)
            
        Returns:
            Dictionary with scan results
        """
        self.stats['total_scanned'] += 1
        
        # Create content hash for caching
        content_hash = hashlib.md5(f"{url}{title}{description}".encode()).hexdigest()
        
        # Check cache first
        if content_hash in self.detection_cache:
            return self.detection_cache[content_hash]
        
        scan_result = {
            'is_nsfw': False,
            'confidence': 0.0,
            'reasons': [],
            'blocked': False,
            'safe_override': False
        }
        
        # 1. Domain-based detection
        is_nsfw_domain, domain_reason = self.is_nsfw_domain(url)
        if is_nsfw_domain:
            scan_result['is_nsfw'] = True
            scan_result['confidence'] += 0.8
            scan_result['reasons'].append(domain_reason)
        
        # 2. URL path analysis
        is_nsfw_path, path_reason = self.analyze_url_path(url)
        if is_nsfw_path:
            scan_result['is_nsfw'] = True
            scan_result['confidence'] += 0.6
            scan_result['reasons'].append(path_reason)
        
        # 3. Title analysis
        if title:
            has_nsfw_title, title_keywords = self.detect_nsfw_keywords(title)
            if has_nsfw_title:
                scan_result['is_nsfw'] = True
                scan_result['confidence'] += 0.7
                scan_result['reasons'].append(f"NSFW title keywords: {title_keywords[:3]}")
        
        # 4. Description analysis
        if description:
            has_nsfw_desc, desc_keywords = self.detect_nsfw_keywords(description)
            if has_nsfw_desc:
                scan_result['is_nsfw'] = True
                scan_result['confidence'] += 0.5
                scan_result['reasons'].append(f"NSFW description keywords: {desc_keywords[:3]}")
        
        # 5. Safe domain override
        parsed = urlparse(url.lower())
        domain = parsed.netloc.replace('www.', '')
        if domain in self.safe_domains:
            scan_result['safe_override'] = True
            scan_result['confidence'] *= 0.3  # Reduce confidence for safe domains
        
        # Final decision
        scan_result['blocked'] = scan_result['is_nsfw'] and scan_result['confidence'] >= 0.5
        
        if scan_result['blocked']:
            self.stats['nsfw_blocked'] += 1
        
        # Cache result
        self.detection_cache[content_hash] = scan_result
        
        return scan_result
    
    def is_content_blocked(self, user_id: int, scan_result: Dict) -> bool:
        """
        Check if content should be blocked based on user preferences
        
        Args:
            user_id: User ID
            scan_result: Result from scan_content()
            
        Returns:
            Boolean indicating if content should be blocked
        """
        # Get user preferences
        if user_id in user_data:
            nsfw_prefs = user_data[user_id].get('nsfw_filter', {})
            
            # Check if NSFW filtering is disabled for this user
            if not nsfw_prefs.get('enabled', True):
                return False
            
            # Check strictness level
            strictness = nsfw_prefs.get('strictness', 'medium')
            
            if strictness == 'off':
                return False
            elif strictness == 'low':
                return scan_result['confidence'] >= 0.8
            elif strictness == 'medium':
                return scan_result['confidence'] >= 0.5
            elif strictness == 'high':
                return scan_result['confidence'] >= 0.3
            elif strictness == 'strict':
                return scan_result['is_nsfw']  # Block any NSFW indicators
        
        # Default behavior - block if confidence >= 0.5
        return scan_result['blocked']
    
    def report_false_positive(self, url: str, user_id: int):
        """Report a false positive for improving the filter"""
        self.stats['false_positives'] += 1
        self.stats['user_reports'] += 1
        
        # Log for manual review
        LOGGER.info(f"NSFW Filter - False positive reported by user {user_id}: {url}")
        
        # Could implement learning mechanism here
    
    def report_missed_content(self, url: str, user_id: int):
        """Report content that should have been blocked"""
        self.stats['user_reports'] += 1
        
        # Log for manual review  
        LOGGER.info(f"NSFW Filter - Missed content reported by user {user_id}: {url}")
    
    def get_stats(self) -> Dict:
        """Get filtering statistics"""
        return self.stats.copy()
    
    def clear_cache(self):
        """Clear the detection cache"""
        self.detection_cache.clear()

# Global filter instance
nsfw_filter = NSFWContentFilter()

# Convenience functions
async def scan_url_for_nsfw(url: str, title: str = "", description: str = "") -> Dict:
    """Scan URL for NSFW content"""
    return await nsfw_filter.scan_content(url, title, description)

def is_nsfw_blocked(user_id: int, scan_result: Dict) -> bool:
    """Check if content should be blocked for user"""
    return nsfw_filter.is_content_blocked(user_id, scan_result)

def report_false_positive(url: str, user_id: int):
    """Report false positive"""
    nsfw_filter.report_false_positive(url, user_id)

def report_missed_content(url: str, user_id: int):
    """Report missed NSFW content"""
    nsfw_filter.report_missed_content(url, user_id)