# 🌐 Language Filter & Enhanced Translation Guide

## ✨ New Features Added:

### **1. Language Filter with Auto-Delete**
- Automatically detects message language
- Deletes messages in unsupported languages
- Supports: **English**, **Hindi**, **Hinglish**
- Configurable per group via settings

### **2. TranslateAI API Integration**
- Better translation accuracy
- Fallback to Deep Translate if AI fails
- Supports 100+ languages
- JSON-aware translation

---

## 🎯 Language Filter Feature

### **How It Works:**

When enabled, the bot will:
1. **Detect** the language of every message
2. **Check** if it's in the allowed list
3. **Delete** messages in unsupported languages
4. **Send warning** (auto-deleted after 10 seconds)

### **Supported Languages:**

| Language | Code | Detection Method |
|----------|------|------------------|
| 🇬🇧 English | `en` | Latin alphabet >70% |
| 🇮🇳 Hindi | `hi` | Devanagari script >70% |
| 💬 Hinglish | `hinglish` | Mix of Hindi + English (both >20%) |

---

## ⚙️ How to Enable Language Filter

### **Step 1: Open Group Settings**
```
/settings
```

### **Step 2: Select Language Filter**
Click: **🌐 Language Filter**

### **Step 3: Configure Settings**

You'll see:
```
🌐 Language Filter Settings

Automatically delete messages in languages other than allowed ones.

Allowed: English, Hindi, Hinglish

[Language Filter: ❌]
[🇬🇧 English: ✅]
[🇮🇳 Hindi: ✅]
[💬 Hinglish: ✅]

[ℹ️ Deletes messages in other languages]
[🔙 Back]
```

### **Step 4: Enable Filter**
Click: **Language Filter: ❌** → Changes to **✅**

### **Step 5: Toggle Languages**
Click on any language to enable/disable it:
- **🇬🇧 English: ✅** → Click to disable
- **🇮🇳 Hindi: ✅** → Click to disable  
- **💬 Hinglish: ✅** → Click to disable

---

## 📋 Use Cases

### **Use Case 1: Only Hindi & English**
```
Settings:
✅ Language Filter: Enabled
✅ English: Enabled
✅ Hindi: Enabled
❌ Hinglish: Disabled

Result:
- English messages: ✅ Allowed
- Hindi messages: ✅ Allowed
- Hinglish messages: ❌ Deleted
- Arabic/Russian/etc: ❌ Deleted
```

### **Use Case 2: Only Hindi**
```
Settings:
✅ Language Filter: Enabled
❌ English: Disabled
✅ Hindi: Enabled
❌ Hinglish: Disabled

Result:
- Only Hindi messages allowed
- Everything else deleted
```

### **Use Case 3: All Three (Default)**
```
Settings:
✅ Language Filter: Enabled
✅ English: Enabled
✅ Hindi: Enabled
✅ Hinglish: Enabled

Result:
- English, Hindi, Hinglish: ✅ Allowed
- Other languages (Arabic, Russian, etc): ❌ Deleted
```

---

## 🧪 Examples

### **Example 1: Russian Message Deleted**
```
User: Привет всем! (Hello everyone in Russian)
Bot: [Deletes message]

⚠️ Language Filter Active

Your message was deleted because it was not in an allowed language.

Detected: OTHER
Allowed: English, Hindi, Hinglish

Please use one of the allowed languages.
[Auto-deletes after 10 seconds]
```

### **Example 2: English Message Allowed**
```
User: Good morning everyone!
Bot: [Message stays - English is allowed]
```

### **Example 3: Hindi Message Allowed**
```
User: नमस्ते सभी को!
Bot: [Message stays - Hindi is allowed]
```

### **Example 4: Hinglish Message Allowed**
```
User: Kya haal hai bhai? सब ठीक है!
Bot: [Message stays - Hinglish is allowed]
```

### **Example 5: Arabic Message Deleted**
```
User: مرحبا بالجميع (Hello everyone in Arabic)
Bot: [Deletes message]

⚠️ Language Filter Active

Detected: OTHER
Allowed: English, Hindi, Hinglish

[Warning auto-deletes after 10s]
```

---

## 🌐 Enhanced Translation Feature

### **What's New:**

**Before:**
- Used only Deep Translate API
- Sometimes failed with errors
- Limited accuracy

**Now:**
- **Primary:** TranslateAI API (better accuracy)
- **Fallback:** Deep Translate API (backup)
- Automatic failover if one API fails
- Better translation quality

### **How Translation Works:**

```
User sends: /tr hi Hello World
         ↓
Bot tries: TranslateAI API
         ↓
    Success? → Shows translation
         ↓
    Failed? → Try Deep Translate API
         ↓
    Success? → Shows translation
         ↓
    Failed? → Shows error
```

### **Translation Commands:**

```
/tr hi Hello World     → Translate to Hindi
/tr en नमस्ते          → Translate to English
/tr es Hello           → Translate to Spanish
/tr fr Hello           → Translate to French

[Reply] /tr            → Translate replied message to Hindi
[Reply] /tr en         → Translate replied message to English
[Reply] /tl            → Open language selection menu
```

---

## 🔧 Technical Details

### **Language Detection Algorithm:**

```python
def detect_language(text):
    - Count Hindi characters (Devanagari Unicode: \u0900-\u097F)
    - Count Latin characters (A-Z, a-z)
    - Calculate percentages
    
    If Hindi > 70% → 'hi'
    If Latin > 70% → 'en'
    If Both > 20% → 'hinglish'
    Otherwise → 'other'
```

### **Translation API Flow:**

```python
async def translate_text(text, source, target):
    1. Try TranslateAI API
       - POST to translateai.p.rapidapi.com
       - JSON-based translation
       - Better accuracy
    
    2. If fails → Try Deep Translate API
       - POST to deep-translate1.p.rapidapi.com
       - Fallback mechanism
    
    3. Return result or None
```

---

## 📊 MongoDB Settings

### **New Settings Added:**

```json
{
  "language_filter_enabled": false,
  "allowed_languages": ["en", "hi", "hinglish"]
}
```

### **Default Values:**
- `language_filter_enabled`: **False** (disabled by default)
- `allowed_languages`: **["en", "hi", "hinglish"]** (all three enabled)

---

## 🎯 Handler Groups

The bot uses handler groups for priority:

```
Group 0:  Moderation, Welcome, Block Content
Group 1:  Clean Service
Group 2:  Auto Delete
Group 3:  Filters
Group 4:  Block Content Messages
Group 5:  Bot Protection
Group 6:  Link Spam Protection
Group 7:  Forward Protection
Group 8:  AI Chat
Group 9:  Translation
Group 10: Language Filter ← NEW!
```

**Language Filter runs last (Group 10)** to ensure other features work first.

---

## ⚠️ Important Notes

### **Admin Messages:**
- Language filter applies to **ALL members** (including admins)
- To allow admin messages, you need to modify the code

### **Bot Commands:**
- Bot commands (`/start`, `/help`, etc.) are **NOT filtered**
- Only regular messages and captions are checked

### **Media Captions:**
- Photo/video captions **ARE filtered**
- If caption is in wrong language, message is deleted

### **Performance:**
- Language detection is **very fast** (local algorithm)
- No API calls needed for detection
- Translation still uses APIs

---

## 🐛 Troubleshooting

### **Issue: Messages not being deleted**
**Solution:**
1. Check if language filter is enabled: `/settings` → 🌐 Language Filter
2. Verify allowed languages include the message language
3. Check bot has delete permissions

### **Issue: Translation failing**
**Solution:**
1. Check server logs: `journalctl -u telegram-bot.service -f`
2. Verify API keys are correct
3. Check if both APIs are accessible

### **Issue: Wrong language detected**
**Solution:**
- Hinglish detection needs both Hindi and English >20%
- Very short messages may be misdetected
- Adjust thresholds in `language_filter.py` if needed

---

## 📝 Files Modified/Created:

### **New Files:**
1. `language_filter.py` - Language detection and filtering
2. `translator_ai.py` - TranslateAI API integration

### **Modified Files:**
1. `settings.py` - Added language filter UI
2. `settings_manager_mongo.py` - Added language settings
3. `translator.py` - Updated to use TranslateAI API
4. `bot.py` - Added language filter handlers

---

## 🚀 Testing Checklist

### **Test Language Filter:**
- [ ] Enable language filter in group settings
- [ ] Send English message → Should stay
- [ ] Send Hindi message → Should stay
- [ ] Send Hinglish message → Should stay
- [ ] Send Russian/Arabic message → Should be deleted
- [ ] Check warning message appears
- [ ] Verify warning auto-deletes after 10s

### **Test Translation:**
- [ ] `/tr hi Hello World` → Should show Hindi
- [ ] `/tr en नमस्ते` → Should show English
- [ ] [Reply] `/tr` → Should translate to Hindi
- [ ] [Reply] `/tr en` → Should translate to English
- [ ] [Reply] `/tl` → Should show language menu

### **Test Settings:**
- [ ] `/settings` → Should show 🌐 Language Filter option
- [ ] Click Language Filter → Should show settings
- [ ] Toggle filter on/off → Should update
- [ ] Toggle individual languages → Should update

---

## 🎉 Summary

**You now have:**

✅ **Language Detection** - Automatically detects EN, HI, Hinglish  
✅ **Auto-Delete** - Removes messages in unsupported languages  
✅ **Configurable** - Enable/disable per language  
✅ **Better Translation** - TranslateAI API with fallback  
✅ **Settings UI** - Easy to configure via `/settings`  
✅ **MongoDB Storage** - Settings saved permanently  

---

**Enjoy your multilingual group management!** 🌐✨
