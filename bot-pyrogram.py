#!/usr/bin/env python3
import os
import re
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

app = Client(
    "colored-buttons-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

def parse_button(button_str):
    style = None
    text = button_str.strip()
    
    color_match = re.match(
        r'^(#g|#r|#p|#o|#y|#pu|#cy|#pk|#go|'
        r'#success|#green|#danger|#red|#primary|#blue|#default|'
        r'#orange|#yellow|#purple|#cyan|#pink|#gold)\s+', text)
    if color_match:
        color_tag = color_match.group(1)
        text = text[len(color_match.group(0)):].strip()
        if color_tag in ["#g", "#success", "#green", "#cy", "#cyan", "#pk", "#pink"]:
            style = enums.ButtonStyle.SUCCESS
        elif color_tag in ["#r", "#danger", "#red", "#pu", "#purple"]:
            style = enums.ButtonStyle.DANGER
        elif color_tag in ["#p", "#primary", "#blue", "#o", "#orange", "#y", "#yellow", "#go", "#gold"]:
            style = enums.ButtonStyle.PRIMARY
        elif color_tag in ["#default"]:
            style = enums.ButtonStyle.DEFAULT
    
    parts = text.split(' - ', 1)
    if len(parts) != 2:
        return None
    
    button_text, button_action = parts
    button = {"text": button_text, "style": style}
    
    if button_action.startswith("popup:"):
        button["type"] = "popup"
        button["popup_text"] = button_action[len("popup:"):]
    elif button_action.startswith("alert:"):
        button["type"] = "alert"
        button["alert_text"] = button_action[len("alert:"):]
    elif button_action.startswith("copy:"):
        button["type"] = "copy"
        button["copy_text"] = button_action[len("copy:"):]
    elif button_action == "comments":
        button["type"] = "comments"
    elif button_action.startswith("share:"):
        button["type"] = "share"
        button["share_text"] = button_action[len("share:"):]
    else:
        button["type"] = "link"
        button["url"] = button_action
    
    return button

def create_button(button_info):
    text = button_info["text"]
    style = button_info["style"]
    
    if button_info["type"] == "link":
        if style:
            return InlineKeyboardButton(
                text=text,
                callback_data=f"link:{style.value}:{button_info['url']}:{text}",
                style=style
            )
        else:
            return InlineKeyboardButton(text=text, url=button_info["url"])
    else:
        if style:
            return InlineKeyboardButton(
                text=text,
                callback_data=f"{style.value}:{text}",
                style=style
            )
        else:
            return InlineKeyboardButton(text=text, callback_data=f"default:{text}")

@app.on_message(filters.command("start"))
async def start(client, message):
    welcome_text = (
        "🤖 Welcome to Colored Buttons Bot!\n\n"
        "Send me button definitions in this format:\n"
        "`Button text - button link`\n\n"
        "For colored buttons:\n"
        "🟢 Green/SUCCESS: `#g Green button - https://example.com` or `#success` or `#green`\n"
        "🔴 Red/DANGER:   `#r Red button - https://example.com` or `#danger` or `#red`\n"
        "🔵 Blue/PRIMARY: `#p Primary button - https://example.com` or `#primary` or `#blue`\n"
        "🟠 Orange:       `#o Orange button - https://example.com` or `#orange`\n"
        "🟡 Yellow:       `#y Yellow button - https://example.com` or `#yellow`\n"
        "🟣 Purple:       `#pu Purple button - https://example.com` or `#purple`\n"
        "🔷 Cyan:         `#cy Cyan button - https://example.com` or `#cyan`\n"
        "🩷 Pink:         `#pk Pink button - https://example.com` or `#pink`\n"
        "✨ Gold:         `#go Gold button - https://example.com` or `#gold`\n"
        "⚪ Default:      `#default Default button - https://example.com`\n\n"
        "For multiple buttons on the same line, use `&&`:\n"
        "`Button1 - link1 && Button2 - link2`\n\n"
        "For multiple rows, use new lines."
    )
    await message.reply_text(welcome_text)

@app.on_message(filters.text)
async def handle_message(client, message):
    if message.text and message.text.startswith("/"):
        return
    message_text = message.text.strip()
    
    if not message_text:
        return
    
    rows = message_text.split("\n")
    keyboard = []
    
    for row in rows:
        buttons_str = row.strip()
        if not buttons_str:
            continue
        
        button_parts = [p.strip() for p in buttons_str.split("&&")]
        row_buttons = []
        
        for part in button_parts:
            button_info = parse_button(part)
            if button_info:
                row_buttons.append(create_button(button_info))
        
        if row_buttons:
            keyboard.append(row_buttons)
    
    if keyboard:
        await message.reply_text(
            "Here are your buttons:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await message.reply_text(
            "❌ Could not parse any buttons. Please check your format."
        )

@app.on_callback_query()
async def button_callback(client, query):
    data = query.data
    
    if data.startswith("link:"):
        parts = data.split(":", 3)
        if len(parts) >= 4:
            style_part = parts[1]
            url = parts[2]
            await query.answer(text="Opening link...", url=url)
        else:
            await query.answer(text="Could not open link", show_alert=True)
    else:
        if ":" in data:
            style_part, text = data.split(":", 1)
        else:
            style_part = "default"
            text = data
        
        style_messages = {
            str(enums.ButtonStyle.SUCCESS.value): "🟢 Success button pressed!",
            str(enums.ButtonStyle.DANGER.value): "🔴 Danger button pressed!",
            str(enums.ButtonStyle.PRIMARY.value): "🔵 Primary button pressed!",
            "default": "⚪ Default button pressed!"
        }
        
        await query.answer(text=style_messages.get(style_part, "Button pressed!"))
        await query.edit_message_text(
            text=f"{style_messages.get(style_part, 'Button pressed!')}\nButton text: {text}"
        )

if __name__ == "__main__":
    print("🤖 Bot is running!")
    app.run()
