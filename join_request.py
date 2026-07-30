import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ChatJoinRequestHandler, CommandHandler, CallbackQueryHandler
from telegram.constants import ParseMode
from settings_manager_mongo import get_chat_settings, update_chat_setting
from user_manager_mongo import is_user_admin
from config import colored_button, log_to_channel, send_bot_response

async def handle_chat_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming chat join requests for a group."""
    join_req = update.chat_join_request
    if not join_req:
        return

    chat = join_req.chat
    user = join_req.from_user
    chat_id = chat.id
    user_id = user.id

async def handle_chat_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming chat join requests for a group."""
    join_req = update.chat_join_request
    if not join_req:
        return

    chat = join_req.chat
    user = join_req.from_user
    chat_id = chat.id
    user_id = user.id

    settings = get_chat_settings(chat_id)
    # Default to manual approval cards in chat
    mode = settings.get("join_request_mode", "manual").lower()

    logging.info(f"Join Request from user {user_id} ({user.first_name}) in chat {chat_id} (mode: {mode})")

    if mode == "accept":
        try:
            await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            logging.info(f"Auto-approved join request for user {user_id} in chat {chat_id}")
            await log_to_channel(context, f"✅ <b>Auto-Approved Join Request</b>\nUser: {user.mention_html()} (<code>{user_id}</code>)\nGroup: <b>{chat.title}</b>")
            
            # Send DM welcome message to the approved user
            from welcome import send_welcome
            await send_welcome(chat, user, context)
        except Exception as e:
            logging.error(f"Error approving join request for {user_id}: {e}")

    elif mode == "decline":
        try:
            await context.bot.decline_chat_join_request(chat_id=chat_id, user_id=user_id)
            logging.info(f"Auto-declined join request for user {user_id} in chat {chat_id}")
            await log_to_channel(context, f"❌ <b>Auto-Declined Join Request</b>\nUser: {user.mention_html()} (<code>{user_id}</code>)\nGroup: <b>{chat.title}</b>")
        except Exception as e:
            logging.error(f"Error declining join request for {user_id}: {e}")

    else:
        # Manual approval card sent in chat with green Accept & red Decline buttons
        accept_btn_text = "#g ✅ Accept"
        reject_btn_text = "#r ❌ Decline"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(accept_btn_text, callback_data=f"joinreq_acc_{chat_id}_{user_id}"),
                InlineKeyboardButton(reject_btn_text, callback_data=f"joinreq_dec_{chat_id}_{user_id}")
            ]
        ])
        msg_text = (
            f"📥 <b>New Join Request</b>\n\n"
            f"👤 <b>User:</b> {user.mention_html()} (<code>{user_id}</code>)\n"
            f"👥 <b>Group:</b> {chat.title}\n\n"
            f"Admins, please accept or decline this request."
        )
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=msg_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logging.error(f"Error sending manual join request alert in chat {chat_id}: {e}")

        # Send DM notification to user that their request is pending approval
        try:
            group_title_html = (chat.title or "the group").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            group_mention = f"@{chat.username}" if getattr(chat, 'username', None) else f"<b>{group_title_html}</b>"
            pending_text = (
                f"⏳ <b>Join Request Received</b>\n\n"
                f"Hello {user.mention_html()}!\n"
                f"Your request to join {group_mention} has been received.\n\n"
                f"📌 <b>Status:</b> <code>Pending Approval</code>\n"
                f"Please wait while group admins review your request."
            )
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=pending_text,
                    parse_mode=ParseMode.HTML
                )
                logging.info(f"Sent join request pending DM notification to user {user_id} for chat {chat_id}")
            except Exception as e:
                err_msg = str(e)
                if "Forbidden" in err_msg or "can't initiate" in err_msg or "chat not found" in err_msg.lower():
                    try:
                        from voice_chat import telethon_client
                        if telethon_client:
                            if not telethon_client.is_connected():
                                await telethon_client.connect()
                            from bio_handler import _resolve_user_entity
                            user_entity = await _resolve_user_entity(telethon_client, user_id, chat_id=chat_id)
                            if user_entity:
                                await telethon_client.send_message(user_entity, pending_text, parse_mode='html')
                                logging.info(f"Sent join request pending DM notification to user {user_id} via Telethon for chat {chat_id}")
                    except Exception as te:
                        logging.debug(f"Telethon pending DM notification failed for user {user_id}: {te}")
        except Exception as pe:
            logging.error(f"Error sending pending notification for user {user_id}: {pe}")


async def join_request_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /joinreq to configure group join request mode."""
    if not update.effective_chat or not update.effective_user:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if update.effective_chat.type == "private":
        await update.message.reply_text("This command can only be used in groups.")
        return

    if not await is_user_admin(chat_id, user_id, context):
        await update.message.reply_text("❌ Admin only command.")
        return

    args = context.args
    settings = get_chat_settings(chat_id)
    current_mode = settings.get("join_request_mode", "manual").lower()

    if args:
        sub = args[0].lower()
        if sub in ["accept", "autoaccept", "approve", "on"]:
            update_chat_setting(chat_id, "join_request_mode", "accept")
            await send_bot_response(update, context, "✅ Join request mode set to: Auto-Accept (Approves automatically & sends DM welcome).")
            return
        elif sub in ["decline", "autodecline", "reject", "off"]:
            update_chat_setting(chat_id, "join_request_mode", "decline")
            await send_bot_response(update, context, "❌ Join request mode set to: Auto-Decline (Declines all join requests).")
            return
        elif sub in ["manual", "ask"]:
            update_chat_setting(chat_id, "join_request_mode", "manual")
            await send_bot_response(update, context, "⚙️ Join request mode set to: Manual (Sends approval cards for admins).")
            return

    # Interactive Settings Panel
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(colored_button("✅ Auto-Accept", "green" if current_mode == "accept" else "default"), callback_data="joinreq_set_accept"),
            InlineKeyboardButton(colored_button("❌ Auto-Decline", "red" if current_mode == "decline" else "default"), callback_data="joinreq_set_decline"),
        ],
        [
            InlineKeyboardButton(colored_button("⚙️ Manual Approval", "blue" if current_mode == "manual" else "default"), callback_data="joinreq_set_manual")
        ]
    ])

    text = (
        f"⚙️ <b>Join Request Settings</b>\n\n"
        f"Current Mode: <b>{current_mode.upper()}</b>\n\n"
        f"Choose how the bot should handle join requests for this group:\n"
        f"• <b>Auto-Accept:</b> Automatically approves join requests and sends welcome DM.\n"
        f"• <b>Auto-Decline:</b> Automatically declines join requests.\n"
        f"• <b>Manual:</b> Prompts admins in group with Accept/Decline buttons."
    )

    await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


async def join_request_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback query handler for join request buttons."""
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data
    user_id = query.from_user.id
    chat_id = update.effective_chat.id if update.effective_chat else None

    # Handle settings toggles
    if data.startswith("joinreq_set_"):
        new_mode = data.replace("joinreq_set_", "")
        if chat_id and await is_user_admin(chat_id, user_id, context):
            update_chat_setting(chat_id, "join_request_mode", new_mode)
            await query.answer(f"Join request mode updated to {new_mode.upper()}!")
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(colored_button("✅ Auto-Accept", "green" if new_mode == "accept" else "default"), callback_data="joinreq_set_accept"),
                    InlineKeyboardButton(colored_button("❌ Auto-Decline", "red" if new_mode == "decline" else "default"), callback_data="joinreq_set_decline"),
                ],
                [
                    InlineKeyboardButton(colored_button("⚙️ Manual Approval", "blue" if new_mode == "manual" else "default"), callback_data="joinreq_set_manual")
                ]
            ])
            text = (
                f"⚙️ <b>Join Request Settings</b>\n\n"
                f"Current Mode: <b>{new_mode.upper()}</b>\n\n"
                f"Choose how the bot should handle join requests for this group:\n"
                f"• <b>Auto-Accept:</b> Automatically approves join requests and sends welcome DM.\n"
                f"• <b>Auto-Decline:</b> Automatically declines join requests.\n"
                f"• <b>Manual:</b> Prompts admins in group with Accept/Decline buttons."
            )
            try:
                await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            except Exception:
                pass
        else:
            await query.answer("Only admins can change settings.", show_alert=True)
        return

    # Handle manual accept/decline buttons: joinreq_acc_{target_chat_id}_{target_user_id}
    if data.startswith("joinreq_acc_") or data.startswith("joinreq_dec_"):
        parts = data.split("_")
        action = parts[1] # 'acc' or 'dec'
        target_chat_id = int(parts[2])
        target_user_id = int(parts[3])

        if not await is_user_admin(target_chat_id, user_id, context):
            await query.answer("❌ Only group admins can respond to join requests.", show_alert=True)
            return

        if action == "acc":
            try:
                await context.bot.approve_chat_join_request(chat_id=target_chat_id, user_id=target_user_id)
                try:
                    from telegram import User
                    group_chat = await context.bot.get_chat(target_chat_id)
                    user_chat = await context.bot.get_chat(target_user_id)
                    user_obj = User(
                        id=target_user_id,
                        first_name=user_chat.first_name or "User",
                        last_name=user_chat.last_name,
                        username=user_chat.username,
                        is_bot=False
                    )
                    await query.edit_message_text(f"✅ Approved join request for {user_obj.mention_html()} (<code>{target_user_id}</code>).", parse_mode=ParseMode.HTML)
                    
                    from welcome import send_welcome
                    await send_welcome(group_chat, user_obj, context)
                except Exception as ex:
                    logging.error(f"Error post-approval for user {target_user_id}: {ex}")
            except Exception as e:
                await query.answer(f"Failed to approve: {e}", show_alert=True)
        elif action == "dec":
            try:
                await context.bot.decline_chat_join_request(chat_id=target_chat_id, user_id=target_user_id)
                await query.answer("❌ Join request declined!")
                try:
                    user_chat = await context.bot.get_chat(target_user_id)
                    await query.edit_message_text(f"❌ Declined join request for {user_chat.first_name} (<code>{target_user_id}</code>).", parse_mode=ParseMode.HTML)
                except Exception:
                    pass
            except Exception as e:
                await query.answer(f"Failed to decline: {e}", show_alert=True)


def get_join_request_handlers():
    """Returns handlers for join requests."""
    return [
        ChatJoinRequestHandler(handle_chat_join_request),
        CommandHandler(["joinreq", "joinrequest"], join_request_command),
        CallbackQueryHandler(join_request_callback, pattern=r"^joinreq_")
    ]
