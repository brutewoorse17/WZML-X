# Auto-Download Feature Documentation

## Overview

The Auto-Download feature automatically detects supported URLs in messages and can initiate downloads without manual commands. This feature enhances user experience by reducing the need to manually trigger downloads for common URL types.

## Features

### 🔍 **Smart URL Detection**
- Automatically detects 12+ different URL types
- Supports 100+ popular domains and services
- Intelligent pattern matching with caching
- Real-time URL analysis and classification

### 📥 **Supported URL Types**

#### **High Priority (Auto-Download)**
- **Google Drive** - Files and folders
- **Mega.nz** - Files and folder links  
- **YouTube** - Videos, playlists, channels
- **Torrent Files** - .torrent downloads
- **Magnet Links** - BitTorrent magnets

#### **Medium Priority (User Confirmation)**
- **Telegram Files** - Direct file links
- **File Hosting** - 50+ popular file hosts
- **Direct Links** - HTTP/HTTPS direct downloads
- **Cloud Storage** - Dropbox, OneDrive, etc.

#### **Low Priority (Manual Only)**
- **Video Streaming** - Various video sites
- **FTP Links** - File transfer protocol
- **Archive Sites** - Archive.org, etc.

### ⚙️ **User Configuration**

#### **Auto-Download Settings** (`/autodownload` or `/ad`)
- **Enable/Disable** - Toggle auto-download functionality
- **Confirmation Prompts** - Ask before downloading
- **URL Type Selection** - Choose which types to auto-download
- **Domain Management** - Whitelist/blacklist specific domains
- **Size Limits** - Set maximum file size for auto-downloads
- **Auto-Extract/Compress** - Automatic file processing

#### **Notification Levels**
- **Silent** - No notifications for auto-downloads
- **Normal** - Basic download notifications
- **Verbose** - Detailed progress and status updates

### 🛡️ **Security Features**

#### **Safe Defaults**
- Only trusted domains auto-download by default
- Unknown/suspicious URLs require user confirmation
- Malicious domain detection and blocking
- File size limits to prevent abuse

#### **User Control**
- Complete control over which URLs to auto-download
- Domain whitelist/blacklist functionality
- Per-user settings and preferences
- Easy enable/disable toggle

## Usage Examples

### **Basic Usage**
Simply send a message with a supported URL:

```
User: Check out this video: https://youtube.com/watch?v=example
Bot: 🤖 Auto-Download Started
     Domain: youtube.com
     Type: video
     ✅ Download initiated successfully!
```

### **Multiple URLs**
The bot can detect and process multiple URLs in a single message:

```
User: Here are some files:
      https://drive.google.com/file/d/example1
      https://mega.nz/file/example2
      
Bot: 🤖 Auto-Download Started (2 URLs detected)
     ✅ Google Drive download initiated
     ✅ Mega download initiated
```

### **User Confirmation**
For uncertain URLs, the bot asks for confirmation:

```
Bot: 🔗 URL Detected
     Domain: unknown-site.com
     Type: filehost
     Would you like to download this?
     [✅ Download] [❌ Skip] [⚙️ Settings]
```

## Commands

### **Main Commands**
- `/autodownload` or `/ad` - Open auto-download settings
- `/adstats` - View auto-download statistics

### **Settings Navigation**
- **Auto-Download Toggle** - Enable/disable feature
- **URL Types** - Select which types to auto-download
- **Domain Settings** - Manage whitelist/blacklist
- **Size Limits** - Set maximum file sizes
- **Notifications** - Configure alert levels

## Technical Implementation

### **Core Components**

1. **URL Auto-Detector** (`bot/helper/ext_utils/url_auto_detector.py`)
   - Comprehensive URL pattern matching
   - Domain categorization and priority system
   - LRU caching for performance
   - Support for 100+ domains

2. **Auto-Download Manager** (`bot/modules/auto_download.py`)
   - Message processing and URL extraction
   - User preference checking
   - Download queue management
   - Confirmation prompt system

3. **Settings Interface** (`bot/modules/auto_download_settings.py`)
   - User preference management
   - Interactive settings menus
   - Database integration
   - Real-time configuration updates

4. **Integration Layer** (`bot/modules/auto_download_integration.py`)
   - Queue-based download processing
   - Error handling and retry logic
   - Statistics tracking
   - Performance optimization

### **Performance Optimizations**

- **LRU Caching** - Frequently accessed URLs cached
- **Queue Processing** - Non-blocking download handling
- **Pattern Compilation** - Pre-compiled regex patterns
- **Batch Processing** - Multiple URLs processed efficiently

### **Database Integration**

User preferences stored in MongoDB:
```json
{
  "auto_download": {
    "enabled": true,
    "prompt_enabled": true,
    "allowed_types": ["gdrive", "mega", "youtube"],
    "domain_whitelist": ["drive.google.com"],
    "domain_blacklist": ["suspicious-site.com"],
    "max_size_mb": 1000,
    "auto_extract": false,
    "auto_compress": false,
    "notification_level": "normal"
  }
}
```

## Configuration Examples

### **Conservative Setup** (Recommended for new users)
```
✅ Auto-Download: Enabled
✅ Confirmation Prompts: Enabled
📋 Allowed Types: Google Drive, Mega, YouTube
🛡️ Security: High (whitelist mode)
📏 Size Limit: 500 MB
```

### **Power User Setup**
```
✅ Auto-Download: Enabled
❌ Confirmation Prompts: Disabled
📋 Allowed Types: All except HTTP/FTP
🛡️ Security: Medium (blacklist mode)
📏 Size Limit: No limit
```

### **Minimal Setup** (Prompts only)
```
❌ Auto-Download: Disabled
✅ Confirmation Prompts: Enabled
📋 Allowed Types: Safe types only
🛡️ Security: Maximum
📏 Size Limit: 100 MB
```

## Statistics and Monitoring

The system tracks:
- **Total URLs Detected** - All URLs found in messages
- **Auto-Downloads** - Successful automatic downloads
- **User Confirmations** - URLs requiring user approval
- **Failed Downloads** - Errors and failures
- **Top Domains** - Most frequently used domains
- **Performance Metrics** - Processing times and queue status

## Troubleshooting

### **Common Issues**

1. **URLs Not Detected**
   - Check if URL type is in allowed list
   - Verify domain isn't blacklisted
   - Ensure auto-download is enabled

2. **Downloads Not Starting**
   - Check bot permissions
   - Verify storage space
   - Review error logs

3. **Too Many Confirmations**
   - Adjust allowed URL types
   - Configure domain whitelist
   - Disable prompts for trusted types

### **Debug Commands**
- `/adstats` - View detailed statistics
- Check logs for error messages
- Test with known working URLs

## Security Considerations

### **Safe Practices**
- Start with conservative settings
- Use domain whitelisting for maximum security
- Set reasonable size limits
- Monitor download activity regularly

### **Risk Mitigation**
- Unknown domains require confirmation
- File size limits prevent abuse
- User can disable feature instantly
- All downloads logged for audit

## Future Enhancements

### **Planned Features**
- **Bulk URL Processing** - Handle large lists efficiently
- **Scheduled Downloads** - Download at specific times
- **Smart Categorization** - Auto-organize downloads
- **Advanced Filtering** - Content-based filtering
- **API Integration** - External service integration

### **Performance Improvements**
- **Parallel Processing** - Multiple concurrent downloads
- **Bandwidth Management** - Smart throttling
- **Cache Optimization** - Enhanced caching strategies
- **Database Indexing** - Faster preference lookups

## Conclusion

The Auto-Download feature significantly enhances the WZML-X bot's usability by automatically detecting and processing supported URLs. With comprehensive user controls, security features, and performance optimizations, it provides a seamless experience while maintaining user safety and system stability.

For support or feature requests, please refer to the bot's help system or contact the administrators.