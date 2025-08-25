# NSFW Auto-Block Feature Documentation

## Overview

The NSFW Auto-Block feature provides comprehensive protection against adult/pornographic content by automatically detecting, filtering, and blocking NSFW URLs and content. This feature ensures appropriate usage of the bot and protects users from unwanted adult content.

## 🛡️ **Core Features**

### **Comprehensive Content Detection**
- **Domain-based filtering** - 200+ known adult sites blocked
- **Keyword analysis** - Advanced pattern matching for NSFW terms
- **URL path scanning** - Analyzes URL structure for adult indicators
- **Context analysis** - Examines titles and descriptions
- **Multi-layer detection** - Combines multiple detection methods

### **Smart Classification System**
- **Confidence scoring** - 0-100% confidence levels
- **Safe domain override** - Whitelisted domains get reduced blocking
- **False positive protection** - Multiple checks before blocking
- **User customization** - Adjustable strictness levels

### **Real-time Protection**
- **Download blocking** - Prevents NSFW downloads automatically
- **Message scanning** - Scans all messages for NSFW URLs
- **Auto-download integration** - Works with auto-download feature
- **Manual command protection** - Blocks /mirror and /leech commands

## 🎚️ **Strictness Levels**

### **Off** ❌
- No NSFW filtering applied
- All content allowed through
- **Use case:** Adult users who want no restrictions

### **Low** 🟢
- Only blocks obvious adult sites
- High confidence threshold (80%+)
- Minimal false positives
- **Use case:** Experienced users who want basic protection

### **Medium** 🟡 (Recommended)
- Balanced filtering approach
- Moderate confidence threshold (50%+)
- Good balance of protection vs. usability
- **Use case:** Most users, families, workplaces

### **High** 🟠
- Aggressive filtering
- Lower confidence threshold (30%+)
- May have some false positives
- **Use case:** Educational environments, strict content control

### **Strict** 🔴
- Maximum protection
- Blocks any suspicious content
- Higher chance of false positives
- **Use case:** Child-safe environments, maximum protection needed

## 🚀 **User Interface & Controls**

### **Main Settings** (`/nsfwfilter`)
```
🛡️ NSFW Content Filter Settings

Filter Status: ✅ Enabled
Strictness: 🟡 Medium - Balanced filtering (Recommended)
Block Downloads: ✅ Enabled
Show Warnings: ✅ Enabled
User Override: ❌ Disabled
Reporting: ✅ Enabled
Auto-Delete: ❌ Disabled

📊 Global Statistics:
• Total Scanned: 1,234
• NSFW Blocked: 89
• False Positives: 3
• User Reports: 12
```

### **Configuration Options**

#### **🔧 Core Settings**
- **NSFW Filter** - Enable/disable the entire system
- **Block Downloads** - Prevent downloads from NSFW URLs
- **Show Warnings** - Display warning messages for flagged content
- **User Override** - Allow users to bypass blocks manually
- **Auto-Delete** - Automatically delete messages with NSFW content

#### **📊 Advanced Options**
- **Reporting** - Enable reporting of false positives/negatives
- **Domain Whitelist** - Always allow specific domains
- **Notification Level** - Control verbosity of alerts
- **Size Limits** - Additional filtering based on file size

## 🔍 **Detection Methods**

### **1. Domain-Based Detection**
```python
Known NSFW Domains: 200+
- Major adult sites (PornHub, XVideos, etc.)
- OnlyFans and similar platforms
- Adult file sharing sites
- Cam sites and adult social networks
- Adult gaming and manga sites
```

### **2. Keyword Analysis**
```python
NSFW Keywords: 100+
- Explicit terms and euphemisms
- Body parts and activities
- Adult content genres
- Platform-specific terms
- Obfuscation patterns (p0rn, s3x, etc.)
```

### **3. URL Path Scanning**
```python
Path Patterns:
- /porn/, /sex/, /adult/
- /category/adult-content
- /watch/xxx-video
- File extensions with adult indicators
```

### **4. Context Analysis**
```python
Content Analysis:
- Message titles and descriptions
- File names and metadata
- Contextual keywords
- Suspicious naming patterns
```

## 📱 **Usage Examples**

### **Basic Blocking**
```
User: /mirror https://adult-site.com/video
Bot:  🚫 NSFW Content Blocked
      
      Domain: adult-site.com
      Confidence: 95%
      Reason: Adult content detected
      
      This URL has been blocked to protect against NSFW content.
      [📝 Report False Positive] [⚙️ Settings]
```

### **Warning for Suspicious Content**
```
User: https://suspicious-domain.com/maybe-adult
Bot:  ⚠️ Potentially NSFW Content
      
      Domain: suspicious-domain.com
      Confidence: 60%
      Status: Allowed but flagged
      
      This content may contain adult material.
      [📝 Report if Safe] [🚫 Report if NSFW]
```

### **Override Request**
```
Bot:  🛑 NSFW Content Detected
      
      Domain: flagged-site.com
      Confidence: 70%
      Status: Blocked by filter
      
      You can override this block if you believe this is safe content.
      [✅ Override & Download] [❌ Keep Blocked] [📝 Report False Positive]
```

## 🧪 **Testing & Validation**

### **URL Testing** (`/nsfwtest`)
```
🧪 NSFW Filter Test Results

URL: https://example.com/content
Domain: example.com

🔍 Detection Results:
• NSFW Detected: ❌ No
• Confidence: 15% ░░░░░░░░░░
• Would Block (You): ❌ No
• Safe Override: ❌ None

🔍 Detection Reasons:
No specific NSFW indicators found

This is a test only - no download was initiated.
```

## 📊 **Statistics & Monitoring**

### **Global Statistics** (`/nsfwstats`)
```
📊 NSFW Filter Statistics

📈 Scanning Activity:
• Total URLs Scanned: 5,432
• NSFW Content Blocked: 234 (4.3%)
• Clean Content Allowed: 5,198

🎯 Accuracy Metrics:
• False Positives Reported: 12 (5.1%)
• Total User Reports: 45

🔧 Filter Database:
• Known NSFW Domains: 200+
• NSFW Keywords: 100+
• Safe Domains: 150+
• Detection Cache Size: 1,024
```

### **Performance Metrics**
- **Detection Speed**: < 50ms average
- **Cache Hit Rate**: 85%+
- **False Positive Rate**: < 5%
- **Memory Usage**: Minimal with LRU caching

## 🔧 **Commands Reference**

### **User Commands**
- `/nsfwfilter` - Open NSFW filter settings
- `/nsfwtest [URL]` - Test URL classification
- `/nsfwstats` - View filter statistics
- `/reportfp [URL]` - Report false positive
- `/reportmissed [URL]` - Report missed NSFW content

### **Settings Navigation**
- **Filter Toggle** - Enable/disable filtering
- **Strictness Levels** - Adjust detection sensitivity
- **Block Downloads** - Control download blocking
- **Show Warnings** - Configure warning messages
- **User Override** - Allow manual overrides
- **Reporting** - Enable/disable reporting features

## 🛡️ **Security & Privacy**

### **Privacy Protection**
- **No content storage** - URLs are hashed for caching only
- **Local processing** - No external API calls for basic detection
- **User data protection** - Settings stored securely
- **Anonymized reporting** - User reports are anonymized

### **Security Features**
- **Bypass protection** - Prevents easy circumvention
- **Admin controls** - Global settings for administrators
- **Audit logging** - All blocks and overrides logged
- **Rate limiting** - Prevents abuse of override features

## 🚀 **Integration Points**

### **Auto-Download Integration**
```python
# NSFW check before auto-download
nsfw_check = await check_nsfw_before_download(url, user_id)
if nsfw_check['blocked']:
    # Block the download and show message
    return
```

### **Mirror/Leech Integration**
```python
# NSFW check in mirror/leech commands
if nsfw_check['blocked']:
    await sendMessage(message, nsfw_check['message'])
    return
```

### **Message Scanning**
```python
# Scan all messages for NSFW content
nsfw_scan_results = await scan_message_nsfw(message)
await handle_nsfw_in_message(message, nsfw_scan_results)
```

## 📈 **Accuracy Improvement**

### **User Reporting System**
- **False Positive Reporting** - `/reportfp [URL]`
- **Missed Content Reporting** - `/reportmissed [URL]`
- **Automatic Learning** - Reports improve future classifications
- **Community Feedback** - Crowdsourced accuracy improvements

### **Continuous Updates**
- **Domain List Updates** - Regular additions to NSFW domain list
- **Keyword Refinement** - Ongoing keyword pattern improvements
- **Algorithm Tuning** - Confidence threshold adjustments
- **Performance Optimization** - Speed and memory improvements

## 🔮 **Advanced Features**

### **Machine Learning Integration** (Future)
- **Content-based detection** - Image/video analysis
- **Behavioral patterns** - User interaction analysis
- **Contextual understanding** - Natural language processing
- **Adaptive filtering** - Personalized detection models

### **Enterprise Features** (Future)
- **Group policies** - Organization-wide settings
- **Compliance reporting** - Audit trails and reports
- **Custom domain lists** - Organization-specific filtering
- **API integration** - External content analysis services

## ⚠️ **Important Notes**

### **Limitations**
- **Not 100% accurate** - Some false positives/negatives expected
- **Language dependent** - Primarily English keyword detection
- **Context limited** - Cannot analyze actual file content
- **Circumvention possible** - Determined users may find workarounds

### **Best Practices**
- **Start with medium strictness** - Good balance for most users
- **Report false positives** - Help improve the system
- **Regular setting reviews** - Adjust based on usage patterns
- **Monitor statistics** - Track effectiveness over time

### **Legal Considerations**
- **Content responsibility** - Users responsible for their content
- **Compliance tool** - Helps with workplace/educational compliance
- **Not legal advice** - Consult legal professionals for compliance needs
- **Regional variations** - Laws vary by jurisdiction

## 🎯 **Conclusion**

The NSFW Auto-Block feature provides comprehensive protection against adult content while maintaining usability and user control. With multiple detection methods, customizable strictness levels, and continuous improvement through user feedback, it offers robust content filtering suitable for various environments from personal use to educational institutions.

The system is designed to be:
- **Effective** - High detection rates with low false positives
- **Customizable** - Adjustable to user needs and preferences
- **Transparent** - Clear reporting of why content was blocked
- **Improvable** - Continuous learning from user feedback
- **Respectful** - Balances protection with user autonomy

For support, feature requests, or questions about the NSFW blocking system, please use the bot's help system or contact administrators.