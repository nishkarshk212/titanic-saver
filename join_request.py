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

    settings = get_chat_settings(chat_id)
    mode = settings.get("join_request_mode", "accept").lower()

    logging.info(f"Join Request from user {user_id} ({user.first_name}) in chat {chat_id} (mode: {mode})")

    if mode == "decline":
        try:
            await context.bot.decline_chat_join_request(chat_id=chat_id, user_id=user_id)
            logging.info(f"Auto-declined join request for user {user_id} in chat {chat_id}")
            await log_to_channel(context, f"❌ <b>Auto-Declined Join Request</b>\nUser: {user.mention_html()} (<code>{user_id}</code>)\nGroup: <b>{chat.title}</b>")
        except Exception as e:
            logging.error(f"Error declining join request for {user_id}: {e}")

    elif mode == "manual":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(colored_button("✅ Accept", "green"), callback_data=f"joinreq_acc_{chat_id}_{user_id}"),
                InlineKeyboardButton(colored_button("❌ Decline", "red"), callback_data=f"joinreq_dec_{chat_id}_{user_id}")
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

    else:
        # Default: auto "accept"
        try:
            await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            logging.info(f"Auto-approved join request for user {user_id} in chat {chat_id}")
            await log_to_channel(context, f"✅ <b>Auto-Approved Join Request</b>\nUser: {user.mention_html()} (<code>{user_id}</code>)\nGroup: <b>{chat.title}</b>")
            
            # Send DM welcome message to the approved user
            from welcome import send_welcome
            await send_welcome(chat, user, context)
        except Exception as e:
            logging.error(f"Error approving join request for {user_id}: {e}")


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
    current_mode = settings.get("join_request_mode", "accept").lower()

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
                await query.answer("✅ Join request approved!")
                try:
                    user_chat = await context.bot.get_chat(target_user_id)
                    await query.edit_message_text(f"✅ Approved join request for {user_chat.first_name} (<code>{target_user_id}</code>).", parse_mode=ParseMode.HTML)
                    
                    # Try sending welcome DM
                    from welcome import send_welcome
                    await send_welcome(user_chat, user_chat, context)
                except Exception:
                    pass
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
