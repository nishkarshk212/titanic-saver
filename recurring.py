from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from settings_manager_mongo import get_chat_settings, update_chat_setting
from config import send_bot_response, edit_bot_response
import logging
import datetime
import asyncio

async def get_recurring_keyboard(settings):
    recurring_messages = settings.get("recurring_messages", [])
    keyboard = []
    
    for msg in recurring_messages:
        msg_id = msg['id']
        active_status = "✅" if msg.get('active', False) else "❌"
        msg_type = msg.get('type', 'time')
        
        type_label = "🕒 Time" if msg_type == 'time' else "💬 Messages"
        interval = msg.get('interval', 1440)
        msg_interval = msg.get('message_interval', 100)
        
        if msg_type == 'time':
            # Convert minutes to readable format
            if interval >= 1440:
                interval_str = f"Every {interval // 1440} days"
            elif interval >= 60:
                interval_str = f"Every {interval // 60} hours"
            else:
                interval_str = f"Every {interval} minutes"
        else:
            interval_str = f"Every {msg_interval} messages"
            
        msg_text = msg.get('text', 'Not set')
        if msg_text and len(msg_text) > 20:
            msg_text = msg_text[:17] + "..."
            
        keyboard.append([InlineKeyboardButton(f"🗯{msg_id} • Active {active_status}", callback_data=f"set_recurring_toggle_active_{msg_id}")])
        keyboard.append([
            InlineKeyboardButton(f"├ Type: {type_label}", callback_data=f"set_recurring_toggle_type_{msg_id}"),
            InlineKeyboardButton(f"└ {interval_str}", callback_data=f"set_recurring_config_interval_{msg_id}")
        ])
        keyboard.append([InlineKeyboardButton(f"📝 Msg: {msg_text}", callback_data=f"set_recurring_config_text_{msg_id}")])
        keyboard.append([InlineKeyboardButton("────────────────────", callback_data="set_none")])
        
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="set_view_main")])
    return InlineKeyboardMarkup(keyboard)

async def recurring_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    chat_id = context.user_data.get('settings_chat_id', update.effective_chat.id)
    settings = get_chat_settings(chat_id)
    recurring_messages = settings.get("recurring_messages", [])
    
    if data == "set_view_recurring":
        await edit_bot_response(
            query, context,
            "🕑 <b>Recurring Messages</b>\n\n"
            "Set messages that will be sent repeatedly to the group every few minutes/hours or every few messages.\n\n"
            f"Current time: {datetime.datetime.now().strftime('%d %b %Y, %H:%M')}",
            reply_markup=await get_recurring_keyboard(settings),
            parse_mode='HTML'
        )
        await query.answer()
        return

    if data.startswith("set_recurring_toggle_active_"):
        msg_id = int(data.split("_")[-1])
        for msg in recurring_messages:
            if msg['id'] == msg_id:
                msg['active'] = not msg.get('active', False)
                break
        update_chat_setting(chat_id, "recurring_messages", recurring_messages)
        await query.edit_message_reply_markup(reply_markup=await get_recurring_keyboard(get_chat_settings(chat_id)))
        await query.answer("Status updated!")
        return

    if data.startswith("set_recurring_toggle_type_"):
        msg_id = int(data.split("_")[-1])
        for msg in recurring_messages:
            if msg['id'] == msg_id:
                msg['type'] = 'messages' if msg.get('type', 'time') == 'time' else 'time'
                break
        update_chat_setting(chat_id, "recurring_messages", recurring_messages)
        await query.edit_message_reply_markup(reply_markup=await get_recurring_keyboard(get_chat_settings(chat_id)))
        await query.answer("Type updated!")
        return

    if data.startswith("set_recurring_config_interval_"):
        msg_id = int(data.split("_")[-1])
        context.user_data['config_recurring_id'] = msg_id
        context.user_data['config_state'] = 'awaiting_recurring_interval'
        
        msg = next((m for m in recurring_messages if m['id'] == msg_id), None)
        msg_type = msg.get('type', 'time')
        
        if msg_type == 'time':
            instruction = "Please enter the interval in minutes (e.g., 60 for 1 hour, 1440 for 1 day):"
        else:
            instruction = "Please enter the message interval (e.g., 100 for every 100 messages):"
            
        await edit_bot_response(
            query, context,
            f"⚙️ <b>Configuring Interval for Message {msg_id}</b>\n\n{instruction}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="set_view_recurring")]]),
            parse_mode='HTML'
        )
        await query.answer()
        return

    if data.startswith("set_recurring_config_text_"):
        msg_id = int(data.split("_")[-1])
        context.user_data['config_recurring_id'] = msg_id
        context.user_data['config_state'] = 'awaiting_recurring_text'
        
        await edit_bot_response(
            query, context,
            f"📝 <b>Configuring Text for Message {msg_id}</b>\n\nPlease send the message you want to be sent repeatedly. You can include media (photo/video).",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="set_view_recurring")]]),
            parse_mode='HTML'
        )
        await query.answer()
        return

async def handle_recurring_config_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('config_state')
    if not state or not state.startswith('awaiting_recurring_'):
        return False
    
    if update.message and update.message.text == "/cancel":
        context.user_data['config_state'] = None
        await update.message.reply_text("❌ Configuration cancelled.")
        return True

    chat_id = context.user_data.get('settings_chat_id')
    if not chat_id:
        return False
        
    msg_id = context.user_data.get('config_recurring_id')
    settings = get_chat_settings(chat_id)
    recurring_messages = settings.get("recurring_messages", [])
    
    target_msg = next((m for m in recurring_messages if m['id'] == msg_id), None)
    if not target_msg:
        return False
        
    if state == 'awaiting_recurring_interval':
        try:
            val = int(update.message.text)
            if val <= 0: raise ValueError
            
            if target_msg['type'] == 'time':
                target_msg['interval'] = val
            else:
                target_msg['message_interval'] = val
                
            update_chat_setting(chat_id, "recurring_messages", recurring_messages)
            await send_bot_response(update, context, "✅ Interval updated successfully!")
        except:
            await send_bot_response(update, context, "❌ Invalid input. Please enter a positive number.")
            return True
            
    elif state == 'awaiting_recurring_text':
        if update.message.text:
            target_msg['text'] = update.message.text
            target_msg['media'] = None
            target_msg['media_type'] = None
        elif update.message.photo:
            target_msg['text'] = update.message.caption
            target_msg['media'] = update.message.photo[-1].file_id
            target_msg['media_type'] = 'photo'
        elif update.message.video:
            target_msg['text'] = update.message.caption
            target_msg['media'] = update.message.video.file_id
            target_msg['media_type'] = 'video'
        elif update.message.animation:
            target_msg['text'] = update.message.caption
            target_msg['media'] = update.message.animation.file_id
            target_msg['media_type'] = 'animation'
        else:
            await send_bot_response(update, context, "❌ Unsupported message type. Please send text, photo, video, or GIF.")
            return True
            
        update_chat_setting(chat_id, "recurring_messages", recurring_messages)
        await send_bot_response(update, context, "✅ Message content updated successfully!")

    # Reset state and show recurring menu
    context.user_data['config_state'] = None
    from settings import show_settings_panel
    await show_settings_panel(update, context, chat_id, is_private=True)
    # We should actually show the recurring menu specifically
    settings = get_chat_settings(chat_id)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🕑 <b>Recurring Messages</b>\n\nUpdated view:",
        reply_markup=await get_recurring_keyboard(settings),
        parse_mode='HTML'
    )
    return True

async def check_recurring_messages(context: ContextTypes.DEFAULT_TYPE):
    """Background job to send recurring messages."""
    from settings_manager_mongo import get_all_chat_settings, update_chat_setting
    
    all_settings = get_all_chat_settings()
    now = datetime.datetime.now()
    
    for chat_id_str, settings in all_settings.items():
        chat_id = int(chat_id_str)
        recurring_messages = settings.get("recurring_messages", [])
        changed = False
        
        for msg in recurring_messages:
            if not msg.get('active', False) or msg.get('type') != 'time':
                continue
                
            last_sent = msg.get('last_sent_at')
            interval_mins = msg.get('interval', 1440)
            
            should_send = False
            if last_sent is None:
                should_send = True
            else:
                if isinstance(last_sent, str):
                    last_sent = datetime.datetime.fromisoformat(last_sent)
                
                if (now - last_sent).total_seconds() / 60 >= interval_mins:
                    should_send = True
            
            if should_send:
                try:
                    text = msg.get('text')
                    media = msg.get('media')
                    media_type = msg.get('media_type')
                    
                    if not text and not media:
                        continue
                        
                    if media:
                        if media_type == 'photo':
                            await context.bot.send_photo(chat_id=chat_id, photo=media, caption=text)
                        elif media_type == 'video':
                            await context.bot.send_video(chat_id=chat_id, video=media, caption=text)
                        elif media_type == 'animation':
                            await context.bot.send_animation(chat_id=chat_id, animation=media, caption=text)
                    else:
                        await context.bot.send_message(chat_id=chat_id, text=text)
                        
                    msg['last_sent_at'] = now.isoformat()
                    changed = True
                except Exception as e:
                    logging.error(f"Error sending recurring message to {chat_id}: {e}")
                    
        if changed:
            update_chat_setting(chat_id, "recurring_messages", recurring_messages)

async def count_recurring_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Message handler to count messages for message-based intervals."""
    if not update.effective_chat or update.effective_chat.type not in ['group', 'supergroup']:
        return
        
    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    recurring_messages = settings.get("recurring_messages", [])
    changed = False
    
    for msg in recurring_messages:
        if not msg.get('active', False) or msg.get('type') != 'messages':
            continue
            
        msg['current_message_count'] = msg.get('current_message_count', 0) + 1
        
        if msg['current_message_count'] >= msg.get('message_interval', 100):
            try:
                text = msg.get('text')
                media = msg.get('media')
                media_type = msg.get('media_type')
                
                if text or media:
                    if media:
                        if media_type == 'photo':
                            await context.bot.send_photo(chat_id=chat_id, photo=media, caption=text)
                        elif media_type == 'video':
                            await context.bot.send_video(chat_id=chat_id, video=media, caption=text)
                        elif media_type == 'animation':
                            await context.bot.send_animation(chat_id=chat_id, animation=media, caption=text)
                    else:
                        await context.bot.send_message(chat_id=chat_id, text=text)
                        
                    msg['current_message_count'] = 0
                    changed = True
            except Exception as e:
                logging.error(f"Error sending message-based recurring message to {chat_id}: {e}")
                
    if changed:
        update_chat_setting(chat_id, "recurring_messages", recurring_messages)

def get_recurring_handlers():
    return [
        CallbackQueryHandler(recurring_callback, pattern="^set_(view_recurring|recurring_toggle_|recurring_config_)"),
        MessageHandler(filters.ALL & ~filters.COMMAND, handle_recurring_config_input)
    ]
