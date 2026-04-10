"""
Translation API Integration using RapidAPI
Provides language translation capabilities for the Telegram bot.
"""

import http.client
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.constants import ParseMode
from config import send_bot_response

# API Configuration
RAPIDAPI_KEY = "79115cebe8msh7aeb0698c33cb2bp140b6cjsn20d3c311c6f4"
RAPIDAPI_HOST = "deep-translate1.p.rapidapi.com"
API_ENDPOINT = "/language/translate/v2"

# Common languages for quick selection
LANGUAGES = {
    "en": "🇬🇧 English",
    "es": "🇪🇸 Spanish",
    "fr": "🇫🇷 French",
    "de": "🇩🇪 German",
    "it": "🇮🇹 Italian",
    "pt": "🇵🇹 Portuguese",
    "ru": "🇷🇺 Russian",
    "zh": "🇨🇳 Chinese",
    "ja": "🇯🇵 Japanese",
    "ko": "🇰🇷 Korean",
    "ar": "🇸🇦 Arabic",
    "hi": "🇮🇳 Hindi",
    "bn": "🇧🇩 Bengali",
    "ur": "🇵🇰 Urdu",
    "tr": "🇹🇷 Turkish",
    "nl": "🇳🇱 Dutch",
    "pl": "🇵🇱 Polish",
    "sv": "🇸🇪 Swedish",
    "da": "🇩🇰 Danish",
    "fi": "🇫🇮 Finnish",
    "el": "🇬🇷 Greek",
    "he": "🇮🇱 Hebrew",
    "th": "🇹🇭 Thai",
    "vi": "🇻🇳 Vietnamese",
    "id": "🇮🇩 Indonesian",
    "ms": "🇲🇾 Malay",
    "ta": "🇮🇳 Tamil",
    "te": "🇮🇳 Telugu",
    "mr": "🇮🇳 Marathi",
    "gu": "🇮🇳 Gujarati"
}

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Translation command handler.
    Usage: /translate <target_lang> <text> or /tr <target_lang> <text>
    Example: /translate es Hello World
    """
    if not context.args or len(context.args) < 2:
        await send_translate_help(update, context)
        return
    
    target_lang = context.args[0].lower()
    text = " ".join(context.args[1:])
    
    # Validate language code
    if target_lang not in LANGUAGES:
        await send_bot_response(
            update, context,
            f"❌ Unsupported language code: {target_lang}\n\n"
            f"Use /translate list to see available languages."
        )
        return
    
    # Show typing action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Detect source language (auto)
    source_lang = "auto"
    
    # Get translation
    translated_text = await translate_text(text, source_lang, target_lang)
    
    if translated_text:
        # Format response
        source_name = "Auto-detected" if source_lang == "auto" else LANGUAGES.get(source_lang, source_lang)
        target_name = LANGUAGES.get(target_lang, target_lang)
        
        response = (
            f"🌐 <b>Translation</b>\n\n"
            f"<b>Original:</b> {text}\n\n"
            f"<b>Translated ({target_name}):</b>\n"
            f"{translated_text}"
        )
        
        await send_bot_response(update, context, response, parse_mode=ParseMode.HTML)
    else:
        await send_bot_response(update, context, "❌ Translation failed. Please try again.")

async def translate_text(text: str, source: str, target: str) -> str:
    """
    Translate text using RapidAPI Translation service.
    
    Args:
        text: Text to translate
        source: Source language code (or 'auto')
        target: Target language code
    
    Returns:
        Translated text or None if error
    """
    try:
        payload = json.dumps({
            "q": text,
            "source": source,
            "target": target
        })
        
        headers = {
            'x-rapidapi-key': RAPIDAPI_KEY,
            'x-rapidapi-host': RAPIDAPI_HOST,
            'Content-Type': "application/json"
        }
        
        # Make API request
        conn = http.client.HTTPSConnection("deep-translate1.p.rapidapi.com")
        conn.request("POST", API_ENDPOINT, payload, headers)
        res = conn.getresponse()
        data = res.read()
        
        if res.status == 200:
            response_data = json.loads(data.decode("utf-8"))
            
            # Extract translated text (adjust based on actual API response structure)
            if "data" in response_data and "translations" in response_data["data"]:
                return response_data["data"]["translations"][0]["translatedText"]
            elif "translatedText" in response_data:
                return response_data["translatedText"]
            elif "translation" in response_data:
                return response_data["translation"]
            elif "result" in response_data:
                return response_data["result"]
            else:
                logging.error(f"Unexpected translation API response: {response_data}")
                return None
        else:
            logging.error(f"Translation API error: {res.status} - {data.decode('utf-8')}")
            return None
            
    except Exception as e:
        logging.error(f"Error in Translation API: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

async def translate_language_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of available languages."""
    language_list = "\n".join([f"• <code>{code}</code> - {name}" for code, name in LANGUAGES.items()])
    
    response = (
        f"🌐 <b>Available Languages</b>\n\n"
        f"{language_list}\n\n"
        f"<b>Usage:</b> /translate &lt;lang_code&gt; &lt;text&gt;\n"
        f"<b>Example:</b> /translate es Hello World"
    )
    
    await send_bot_response(update, context, response, parse_mode=ParseMode.HTML)

async def translate_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show translation menu with language options."""
    if not context.args:
        await send_translate_help(update, context)
        return
    
    text = " ".join(context.args)
    
    # Create keyboard with popular languages
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="translate_en"),
            InlineKeyboardButton("🇪🇸 Spanish", callback_data="translate_es"),
        ],
        [
            InlineKeyboardButton("🇫🇷 French", callback_data="translate_fr"),
            InlineKeyboardButton("🇩🇪 German", callback_data="translate_de"),
        ],
        [
            InlineKeyboardButton("🇮🇹 Italian", callback_data="translate_it"),
            InlineKeyboardButton("🇷🇺 Russian", callback_data="translate_ru"),
        ],
        [
            InlineKeyboardButton("🇨🇳 Chinese", callback_data="translate_zh"),
            InlineKeyboardButton("🇯🇵 Japanese", callback_data="translate_ja"),
        ],
        [
            InlineKeyboardButton("🇮🇳 Hindi", callback_data="translate_hi"),
            InlineKeyboardButton("🇸🇦 Arabic", callback_data="translate_ar"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="translate_cancel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Store text in user_data for callback access
    context.user_data[f"translate_text_{update.effective_user.id}"] = text
    
    response = (
        f"📝 <b>Text to translate:</b>\n\n"
        f"\"{text}\"\n\n"
        f"👇 <b>Select target language:</b>"
    )
    
    await send_bot_response(update, context, response, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def translate_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle translation callback queries."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    await query.answer()
    
    # Get stored text
    text = context.user_data.get(f"translate_text_{user_id}")
    if not text:
        await query.edit_message_text("❌ No text found for translation. Use /translate <text> first.")
        return
    
    data = query.data
    
    if data == "translate_cancel":
        await query.edit_message_text("❌ Translation cancelled.")
        return
    
    # Extract language code
    target_lang = data.replace("translate_", "")
    
    # Show typing action
    await context.bot.send_chat_action(chat_id=query.message.chat_id, action="typing")
    
    # Perform translation
    translated_text = await translate_text(text, "auto", target_lang)
    
    if translated_text:
        target_name = LANGUAGES.get(target_lang, target_lang)
        
        response = (
            f"🌐 <b>Translation</b>\n\n"
            f"<b>Original:</b> {text}\n\n"
            f"<b>Translated ({target_name}):</b>\n"
            f"{translated_text}"
        )
        
        await query.edit_message_text(response, parse_mode=ParseMode.HTML)
    else:
        await query.edit_message_text("❌ Translation failed. Please try again.")

async def send_translate_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send translation help message."""
    response = (
        f"🌐 <b>Translation Service</b>\n\n"
        f"<b>Commands:</b>\n"
        f"• /translate &lt;lang&gt; &lt;text&gt; - Translate text\n"
        f"• /tr &lt;lang&gt; &lt;text&gt; - Short command\n"
        f"• /tl &lt;text&gt; - Open language menu\n"
        f"• /langs - Show available languages\n\n"
        f"<b>Examples:</b>\n"
        f"• /translate es Hello World\n"
        f"• /tr fr Good morning\n"
        f"• /tl How are you?\n\n"
        f"Use /translate list or /langs to see all supported languages."
    )
    
    await send_bot_response(update, context, response, parse_mode=ParseMode.HTML)

def get_translation_handlers():
    """Return all translation handlers."""
    return [
        CommandHandler("translate", translate_command),
        CommandHandler("tr", translate_command),
        CommandHandler("tl", translate_menu),
        CommandHandler("langs", translate_language_list),
        CallbackQueryHandler(translate_callback_handler, pattern="^translate_")
    ]
