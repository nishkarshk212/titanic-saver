# AI Chat & Translation Features Guide

## 🤖 New Features Added

Your Telegram bot now includes two powerful AI features:

### 1. AI Chat (ChatGPT Integration)
### 2. Language Translation

---

## 🤖 AI Chat Feature

### Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/ai <message>` | Chat with AI | `/ai What is Python?` |
| `/gpt <message>` | Same as /ai | `/gpt Write a poem` |
| `/clearchat` | Clear conversation history | `/clearchat` |

### Features

✅ **Conversational AI** - Maintains context across messages
✅ **Multi-turn Conversations** - Remembers last 10 messages
✅ **Smart Responses** - Powered by ChatGPT-4
✅ **Private Chat Support** - Chat directly with bot in PM
✅ **Mention Support** - Mention bot in groups to ask questions

### Usage Examples

```
/ai What is machine learning?
/ai Explain quantum physics in simple terms
/ai Write a Python function to sort a list
/ai Translate "Hello" to French
/gpt What are the benefits of exercise?
```

### How It Works

1. **Direct Command**: Use `/ai` or `/gpt` followed by your message
2. **Private Chat**: Just send messages directly to the bot
3. **Group Mention**: Mention the bot with `@YourBotName your question`

### Conversation History

- The bot remembers your last 10 messages
- Use `/clearchat` to reset the conversation
- Each user has their own separate conversation

---

## 🌐 Translation Feature

### Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/translate <lang> <text>` | Translate text | `/translate es Hello World` |
| `/tr <lang> <text>` | Short command | `/tr fr Good morning` |
| `/tl <text>` | Open language menu | `/tl How are you?` |
| `/langs` | Show all languages | `/langs` |

### Supported Languages (40+)

| Code | Language | Code | Language |
|------|----------|------|----------|
| `en` | 🇬🇧 English | `es` | 🇪🇸 Spanish |
| `fr` | 🇫🇷 French | `de` | 🇩🇪 German |
| `it` | 🇮🇹 Italian | `pt` | 🇵🇹 Portuguese |
| `ru` | 🇷🇺 Russian | `zh` | 🇨🇳 Chinese |
| `ja` | 🇯🇵 Japanese | `ko` | 🇰🇷 Korean |
| `ar` | 🇸🇦 Arabic | `hi` | 🇮🇳 Hindi |
| `bn` | 🇧🇩 Bengali | `ur` | 🇵🇰 Urdu |
| `tr` | 🇹🇷 Turkish | `nl` | 🇳🇱 Dutch |
| `pl` | 🇵🇱 Polish | `sv` | 🇸🇪 Swedish |
| And 20+ more languages! |

### Usage Examples

**Direct Translation:**
```
/translate es Hello World
/tr fr Good morning everyone
/translate ja Thank you very much
```

**Interactive Menu:**
```
/tl How are you today?
```
This will show a button menu to select the target language.

**List Languages:**
```
/langs
```

### Features

✅ **40+ Languages** - Support for major world languages
✅ **Auto-Detection** - Automatically detects source language
✅ **Interactive Menu** - Easy language selection with buttons
✅ **Fast Translation** - Powered by Deep Translate API
✅ **Group Support** - Works in both groups and private chats

---

## 🔧 API Configuration

### ChatGPT API
- **Provider**: RapidAPI (ChatGPT-42)
- **Endpoint**: `chatgpt-42.p.rapidapi.com`
- **Rate Limit**: Depends on your RapidAPI plan

### Translation API
- **Provider**: RapidAPI (Deep Translate)
- **Endpoint**: `deep-translate1.p.rapidapi.com`
- **Rate Limit**: Depends on your RapidAPI plan

### API Keys

Both APIs use the same RapidAPI key:
```
X-RapidAPI-Key: 79115cebe8msh7aeb0698c33cb2bp140b6cjsn20d3c311c6f4
```

**Note**: For production use, move API keys to `.env` file:

```env
# .env file
RAPIDAPI_KEY=your_api_key_here
```

---

## 📋 Complete Command List

### AI Commands
- `/ai <message>` - Chat with AI
- `/gpt <message>` - Chat with AI (alias)
- `/clearchat` - Clear AI conversation history

### Translation Commands
- `/translate <lang> <text>` - Translate text
- `/tr <lang> <text>` - Short translation command
- `/tl <text>` - Open translation language menu
- `/langs` - List all supported languages

---

## 🎯 Use Cases

### AI Chat Examples

1. **Learning & Education**
   ```
   /ai Explain photosynthesis
   /ai What is the theory of relativity?
   ```

2. **Writing Assistance**
   ```
   /ai Write an email to my boss
   /ai Help me write a resume
   ```

3. **Programming Help**
   ```
   /ai How to create a Flask app?
   /ai Explain async/await in Python
   ```

4. **Creative Writing**
   ```
   /ai Write a short story about space
   /ai Create a poem about nature
   ```

### Translation Examples

1. **Business Communication**
   ```
   /translate es Meeting at 3 PM tomorrow
   /translate fr Thank you for your cooperation
   ```

2. **Social Media**
   ```
   /translate ja I love Japanese food!
   /translate ko K-pop is amazing
   ```

3. **Travel**
   ```
   /translate es Where is the nearest hotel?
   /translate de How much does this cost?
   ```

4. **Learning Languages**
   ```
   /translate en Bonjour, comment allez-vous?
   /tr ja こんにちは
   ```

---

## ⚙️ Technical Details

### File Structure

```
ai_chat.py          - ChatGPT integration
translator.py       - Translation service
bot.py              - Main bot file (updated)
```

### Integration Points

Both features are integrated as separate modules:
- `ai_chat.py` - Handles all AI conversation features
- `translator.py` - Handles all translation features

### Handler Groups

- Group 8: AI Chat handlers
- Group 9: Translation handlers

This ensures proper message processing order.

---

## 🚀 Testing the Features

### Test AI Chat

1. Start your bot
2. Send: `/ai Hello, how are you?`
3. The bot should respond with an AI-generated message
4. Try follow-up questions to test conversation memory

### Test Translation

1. Send: `/translate es Hello World`
2. You should see: "Hola Mundo"
3. Try: `/tl Good morning`
4. Select a language from the button menu

---

## 🔒 Security & Privacy

### API Key Security

⚠️ **Important**: Your API keys are currently hardcoded. For production:

1. Move to `.env` file:
   ```env
   RAPIDAPI_KEY=your_key_here
   ```

2. Update `ai_chat.py` and `translator.py`:
   ```python
   import os
   RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
   ```

3. Add to `.gitignore`:
   ```
   .env
   ```

### Rate Limits

- Monitor your RapidAPI usage
- Implement rate limiting if needed
- Consider upgrading plan for high usage

### Data Privacy

- Conversation history is stored in memory only
- History is cleared on bot restart
- Users can clear history with `/clearchat`
- No personal data is stored permanently

---

## 🐛 Troubleshooting

### AI Chat Not Working

**Problem**: Bot doesn't respond to `/ai` commands
**Solutions**:
1. Check API key is valid
2. Verify RapidAPI subscription is active
3. Check bot logs for API errors
4. Ensure internet connection is working

### Translation Failing

**Problem**: Translation returns error
**Solutions**:
1. Verify language code is correct
2. Check API key permissions
3. Ensure text is not too long
4. Check RapidAPI quota

### Rate Limit Errors

**Problem**: Too many requests error
**Solutions**:
1. Wait and try again
2. Upgrade RapidAPI plan
3. Implement cooldown between requests
4. Monitor API usage dashboard

---

## 📊 API Usage Monitoring

### Check Usage

Visit RapidAPI dashboard:
- ChatGPT API: https://rapidapi.com/
- Translation API: https://rapidapi.com/

### Monitor Metrics

- Daily request count
- Response times
- Error rates
- Quota usage

---

## 🎓 Advanced Configuration

### Customize AI Behavior

Edit `ai_chat.py`:

```python
# Change temperature (creativity)
"temperature": 0.9  # 0.0-1.0 (higher = more creative)

# Change max response length
"max_tokens": 512  # Increase for longer responses

# Add system prompt
"system_prompt": "You are a helpful assistant."
```

### Add More Languages

Edit `translator.py`:

```python
LANGUAGES = {
    # Add new languages
    "xx": "🏳️ Language Name",
}
```

---

## 📝 Future Enhancements

Potential improvements:

- [ ] Image generation (DALL-E)
- [ ] Voice message translation
- [ ] Document translation
- [ ] AI image analysis
- [ ] Multi-language AI responses
- [ ] Translation history
- [ ] Favorite languages
- [ ] Auto-translate mode

---

## 🆘 Support

### Getting Help

1. Check bot logs for errors
2. Verify API keys are valid
3. Test APIs directly on RapidAPI
4. Check RapidAPI documentation

### Common Issues

**SSL Errors**: See MongoDB setup guide
**API Errors**: Check RapidAPI dashboard
**Bot Offline**: Verify bot token and internet

---

## ✅ Quick Checklist

Before deploying:

- [ ] Test `/ai` command
- [ ] Test `/translate` command
- [ ] Verify API keys work
- [ ] Check rate limits
- [ ] Move keys to `.env`
- [ ] Update `.gitignore`
- [ ] Monitor API usage
- [ ] Test in groups
- [ ] Test in private chats

---

**Enjoy your AI-powered Telegram bot! 🚀**
