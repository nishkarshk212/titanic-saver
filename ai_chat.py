"""
ChatGPT API Integration using RapidAPI
Provides AI conversation capabilities for the Telegram bot.
"""

import http.client
import json
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from config import send_bot_response

# API Configuration
RAPIDAPI_KEY = "79115cebe8msh7aeb0698c33cb2bp140b6cjsn20d3c311c6f4"
RAPIDAPI_HOST = "chatgpt-42.p.rapidapi.com"
API_ENDPOINT = "/conversationgpt4-2"

# Store conversation history per user
conversation_history = {}

async def chatgpt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ChatGPT command handler.
    Usage: /ai <your message> or /gpt <your message>
    """
    if not context.args:
        await send_bot_response(
            update, context,
            "🤖 <b>AI Assistant</b>\n\n"
            "Usage: /ai <your message>\n\n"
            "Examples:\n"
            "• /ai What is Python?\n"
            "• /ai Write a short poem\n"
            "• /ai Explain quantum physics"
        )
        return

    user_message = " ".join(context.args)
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Show typing action
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # Get response from ChatGPT
    response = await get_chatgpt_response(user_message, user_id)
    
    if response:
        # Format and send response
        formatted_response = f"🤖 <b>AI Response:</b>\n\n{response}"
        await send_bot_response(update, context, formatted_response, parse_mode="HTML")
    else:
        await send_bot_response(update, context, "❌ Sorry, I couldn't get a response from AI. Please try again later.")

async def get_chatgpt_response(message: str, user_id: int, system_prompt: str = "") -> str:
    """
    Get response from ChatGPT API.
    
    Args:
        message: User's message
        user_id: User ID for conversation history
        system_prompt: Optional system prompt
    
    Returns:
        AI response text or None if error
    """
    try:
        # Initialize conversation history for user if not exists
        if user_id not in conversation_history:
            conversation_history[user_id] = []
        
        # Add user message to history
        conversation_history[user_id].append({
            "role": "user",
            "content": message
        })
        
        # Keep only last 10 messages to avoid token limits
        if len(conversation_history[user_id]) > 10:
            conversation_history[user_id] = conversation_history[user_id][-10:]
        
        # Prepare payload
        payload = json.dumps({
            "messages": conversation_history[user_id],
            "system_prompt": system_prompt,
            "temperature": 0.9,
            "top_k": 5,
            "top_p": 0.9,
            "max_tokens": 512,
            "web_access": False
        })
        
        headers = {
            'x-rapidapi-key': RAPIDAPI_KEY,
            'x-rapidapi-host': RAPIDAPI_HOST,
            'Content-Type': "application/json"
        }
        
        # Make API request
        conn = http.client.HTTPSConnection("chatgpt-42.p.rapidapi.com")
        conn.request("POST", API_ENDPOINT, payload, headers)
        res = conn.getresponse()
        data = res.read()
        
        if res.status == 200:
            response_data = json.loads(data.decode("utf-8"))
            
            # Extract response text (adjust based on actual API response structure)
            if "result" in response_data:
                ai_response = response_data["result"]
                # Add AI response to history
                conversation_history[user_id].append({
                    "role": "assistant",
                    "content": ai_response
                })
                return ai_response
            elif "response" in response_data:
                ai_response = response_data["response"]
                conversation_history[user_id].append({
                    "role": "assistant",
                    "content": ai_response
                })
                return ai_response
            elif "message" in response_data:
                ai_response = response_data["message"]
                conversation_history[user_id].append({
                    "role": "assistant",
                    "content": ai_response
                })
                return ai_response
            else:
                logging.error(f"Unexpected ChatGPT API response: {response_data}")
                return None
        else:
            logging.error(f"ChatGPT API error: {res.status} - {data.decode('utf-8')}")
            return None
            
    except Exception as e:
        logging.error(f"Error in ChatGPT API: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def clear_conversation(user_id: int):
    """Clear conversation history for a user."""
    if user_id in conversation_history:
        del conversation_history[user_id]

async def clear_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history for the user."""
    user_id = update.effective_user.id
    clear_conversation(user_id)
    await send_bot_response(update, context, "🗑️ Conversation history cleared!")

async def ai_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle AI chat messages when bot is mentioned or in private chat.
    """
    # Only respond in private chats or when bot is mentioned
    if update.effective_chat.type == "private":
        message = update.message.text
        user_id = update.effective_user.id
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        response = await get_chatgpt_response(message, user_id)
        
        if response:
            await send_bot_response(update, context, response)
    elif update.message.entities:
        # Check if bot is mentioned
        for entity in update.message.entities:
            if entity.type == "mention":
                username_text = update.message.text[entity.offset:entity.offset+entity.length]
                bot_username = await context.bot.get_me()
                if f"@{bot_username.username}" == username_text:
                    # Extract message after mention
                    message = update.message.text.replace(username_text, "").strip()
                    if message:
                        user_id = update.effective_user.id
                        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
                        response = await get_chatgpt_response(message, user_id)
                        
                        if response:
                            await send_bot_response(update, context, response)
                        break

def get_chatgpt_handlers():
    """Return all ChatGPT handlers."""
    return [
        CommandHandler("ai", chatgpt_command),
        CommandHandler("gpt", chatgpt_command),
        CommandHandler("clearchat", clear_chat_command),
        MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat_handler)
    ]
