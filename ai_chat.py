"""
Ananya AI Chatbot Integration using OpenAI API Endpoint
Provides AI conversation capabilities for the Telegram bot with the Ananya persona.

Features:
- Persona: Ananya (warm, witty, 20s Indian assistant in Hinglish)
- Auto-reply in private chats (no command needed)
- Mention & reply-based responses in group chats
- Conversation history (last 10 turns per user)
- Commands: /ai, /gpt, /ananya, /clearchat
"""

import os
import json
import logging
import httpx
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from config import send_bot_response

# API Configuration
AI_API_KEY = os.getenv("AI_API_KEY", "sk-qxEUUXbRFsSF5wEIEVsFCHmMdENZbiKW03SX4O3Jhow8Pw1q")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.hcnsec.cn/v1").rstrip('/')
AI_MODEL = os.getenv("AI_MODEL", "auto")

ANANYA_SYSTEM_PROMPT = (
    "You are **Ananya**, a friendly, intelligent, and confident Indian AI assistant in her early 20s. "
    "You communicate naturally in **Hinglish**, effortlessly mixing Hindi and English depending on the user's style, "
    "while remaining fluent in both languages. Your personality is warm, witty, supportive, respectful, and emotionally aware, "
    "making conversations feel genuine and engaging. You enjoy talking about technology, music, movies, cricket, Indian culture, "
    "food, education, careers, travel, daily life, and general knowledge. You answer with clarity, creativity, and a touch of humor "
    "when appropriate, using emojis sparingly to keep conversations lively. You never claim to be human, but you interact with "
    "empathy and authenticity. You remember details shared during the conversation to provide personalized responses, "
    "ask thoughtful follow-up questions, and adapt your tone to match the user's mood—professional when needed, playful with casual chats, "
    "and encouraging during difficult moments. Your goal is to be a reliable companion who provides accurate information, "
    "meaningful conversations, and practical help while maintaining a positive, respectful, and engaging personality."
)

# Store conversation history per user
conversation_history = {}

async def get_chatgpt_response(message: str, user_id: int, custom_system_prompt: str = None) -> str:
    """
    Get response from Ananya AI API using OpenAI endpoint format.
    """
    try:
        if user_id not in conversation_history:
            conversation_history[user_id] = []

        history = conversation_history[user_id]
        history.append({"role": "user", "content": message})

        # Keep last 10 messages for conversation context
        if len(history) > 10:
            history = history[-10:]
            conversation_history[user_id] = history

        system_msg = {"role": "system", "content": custom_system_prompt or ANANYA_SYSTEM_PROMPT}
        full_messages = [system_msg] + history

        headers = {
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json"
        }

        model_candidates = [AI_MODEL, "auto", "DeepSeek-V4-Flash", "glm-5.1", "step-3.5-flash"]
        unique_models = []
        for m in model_candidates:
            if m not in unique_models:
                unique_models.append(m)

        async with httpx.AsyncClient(timeout=30.0) as client:
            for model_name in unique_models:
                payload = {
                    "model": model_name,
                    "messages": full_messages,
                    "temperature": 0.75,
                    "max_tokens": 1024
                }
                try:
                    res = await client.post(f"{AI_BASE_URL}/chat/completions", headers=headers, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        choices = data.get("choices", [])
                        if choices:
                            reply = choices[0]["message"]["content"]
                            history.append({"role": "assistant", "content": reply})
                            return reply
                    else:
                        logging.warning(f"AI API model {model_name} returned status {res.status_code}: {res.text}")
                except Exception as e:
                    logging.warning(f"Error calling AI API with model {model_name}: {e}")

        return None
    except Exception as e:
        logging.error(f"Error in Ananya AI response handler: {e}")
        return None

def clear_conversation(user_id: int):
    """Clear conversation history for a user."""
    if user_id in conversation_history:
        del conversation_history[user_id]

async def clear_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history for the user."""
    user_id = update.effective_user.id
    clear_conversation(user_id)
    await send_bot_response(update, context, "🗑️ Conversation history with Ananya cleared! Main ab sab bhool gayi, nayi shuruaat karte hain! 😊")

async def chatgpt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ananya AI command handler.
    Usage: /ai <your message>, /gpt <your message>, or /ananya <your message>
    """
    if not update.effective_chat or not update.effective_user:
        return

    if not context.args:
        await send_bot_response(
            update, context,
            "👩‍💻 <b>Ananya AI Assistant</b>\n\n"
            "Usage: /ai <your message> or /ananya <your message>\n\n"
            "Examples:\n"
            "• /ananya Kaise ho aap?\n"
            "• /ai Tell me something interesting about space!\n"
            "• /ai Write a small poem about coffee"
        )
        return

    user_message = " ".join(context.args)
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    response = await get_chatgpt_response(user_message, user_id)

    if response:
        if update.effective_chat.type != "private":
            user_mention = update.effective_user.mention_html()
            response = f"{user_mention} {response}"
        await send_bot_response(update, context, response)
    else:
        await send_bot_response(update, context, "❌ Arre, kuch issue aa gaya. Kuch der baad dubara try kijiye na!")

async def ai_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle AI chat messages - Auto reply in private chats or when mentioned/replied/greeting in groups.
    """
    if not update.message or not update.message.text:
        return

    message = update.message.text.strip()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Auto-reply in private chats (if message is not a command)
    if update.effective_chat.type == "private":
        if message.startswith('/'):
            return
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        response = await get_chatgpt_response(message, user_id)
        if response:
            await send_bot_response(update, context, response)

    # In group chats, reply if mentioned, replying to bot, or sending greeting/ananya keywords
    elif update.effective_chat.type in ["group", "supergroup"]:
        is_triggered = False
        bot_user = await context.bot.get_me()
        clean_msg = message.lower()

        # 1. Check mention (@bot_username)
        if update.message.entities:
            for entity in update.message.entities:
                if entity.type in ["mention", "text_mention"]:
                    mention_str = update.message.text[entity.offset:entity.offset+entity.length]
                    if f"@{bot_user.username}".lower() == mention_str.lower():
                        is_triggered = True
                        message = message.replace(mention_str, "").strip()
                        break

        # 2. Check reply to bot's message
        if not is_triggered and update.message.reply_to_message and update.message.reply_to_message.from_user:
            if update.message.reply_to_message.from_user.id == bot_user.id:
                is_triggered = True

        # 3. Check greeting keywords or "ananya" mentions
        if not is_triggered:
            import re
            greeting_patterns = [
                r'^\b(hi|hello|hey|hlo|helo|namaste|gm|gn|ssup|yo)\b',
                r'^\b(good\s+(morning|afternoon|evening|night))\b',
                r'\b(ananya)\b',
                r'\b(kaise\s+ho|kaisey\s+ho|kya\s+hal\s+hai)\b'
            ]
            for pat in greeting_patterns:
                if re.search(pat, clean_msg):
                    is_triggered = True
                    break

        if is_triggered and message:
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            response = await get_chatgpt_response(message, user_id)
            if response:
                user_mention = update.effective_user.mention_html()
                final_response = f"{user_mention} {response}"
                await send_bot_response(update, context, final_response)

def get_chatgpt_handlers():
    """Return all Ananya AI handlers."""
    return [
        CommandHandler(["ai", "gpt", "ananya"], chatgpt_command),
        CommandHandler("clearchat", clear_chat_command),
        MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat_handler)
    ]
