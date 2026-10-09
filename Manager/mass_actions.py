"""
Manager Mass Actions - kickall, banall, unbanall, unabnall, muteall, unmuteall, unpinall
Ported from AnnieXMusic to python-telegram-bot
"""

import asyncio
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.constants import ChatMemberStatus
from settings_manager_mongo import get_chat_settings
from Manager.actions import check_admin_permission, check_bot_permission

MASS_CMDS = ["kickall", "banall", "unbanall", "unabnall", "muteall", "unmuteall", "unpinall"]

def confirmation_keyboard(cmd):
    """Create confirmation keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Yes", callback_data=f"{cmd}_yes"),
         InlineKeyboardButton("No", callback_data=f"{cmd}_no")]
    ])

async def ask_mass_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for confirmation before mass action."""
    cmd = update.message.command[0].lower() if update.message.command else (context.args[0].lower() if context.args else None)
    if not cmd or cmd not in MASS_CMDS:
        return
    
    chat = update.effective_chat
    user = update.effective_user

    if not chat or chat.type in ['private']:
        return await update.message.reply_text("❌ Mass action commands can only be used in groups.")
    
    # Check if mass actions are enabled
    settings = get_chat_settings(chat.id)
    if not settings.get("manager_mass_actions_enabled", True):
        return await update.message.reply_text("❌ Mass action commands are currently disabled.")
    
    # Permission check
    if cmd == 'unpinall':
        permission = 'can_pin_messages'
    elif cmd in ['kickall', 'banall', 'unbanall', 'unabnall']:
        permission = 'can_ban_users'
    else: # muteall, unmuteall
        permission = 'can_restrict_members'
        
    has_perm, error_msg = await check_admin_permission(update, context, permission)
    if not has_perm:
        return await update.message.reply_text(error_msg)
    
    # Bot permission check
    has_bot_perm, bot_error_msg = await check_bot_permission(update, context, permission)
    if not has_bot_perm:
        return await update.message.reply_text(bot_error_msg)
    
    # Direct confirmation via flag (e.g. /unbanall yes or /unabnall -y)
    if context.args and context.args[0].lower() in ['yes', 'confirm', '-y', '-f', 'force']:
        status_msg = await update.message.reply_text(f"⏳ `{cmd}` in progress…", parse_mode='HTML')
        try:
            if cmd == "kickall":
                await do_kickall(context.bot, chat.id, status_msg)
            elif cmd == "banall":
                await do_banall(context.bot, chat.id, status_msg)
            elif cmd in ["unbanall", "unabnall"]:
                await do_unbanall(context.bot, chat.id, status_msg)
            elif cmd == "muteall":
                await do_muteall(context.bot, chat.id, status_msg)
            elif cmd == "unmuteall":
                await do_unmuteall(context.bot, chat.id, status_msg)
            elif cmd == "unpinall":
                await do_unpinall(context.bot, chat.id, status_msg)
        except Exception as e:
            await status_msg.edit_text(f"❌ Error during `{cmd}`:\n{str(e)}", parse_mode='HTML')
        return

    await update.message.reply_text(
        f"⚠️ {user.mention_html()}, confirm `{cmd}` for this group?",
        reply_markup=confirmation_keyboard(cmd),
        parse_mode='HTML'
    )

async def handle_mass_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle mass action confirmation."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    match = re.match(r'^(kickall|banall|unbanall|unabnall|muteall|unmuteall|unpinall)_(yes|no)$', data)
    if not match:
        return
    
    cmd, answer = match.groups()
    chat_id = query.message.chat_id
    
    # Permission check
    if cmd == 'unpinall':
        permission = 'can_pin_messages'
    elif cmd in ['kickall', 'banall', 'unbanall', 'unabnall']:
        permission = 'can_ban_users'
    else: # muteall, unmuteall
        permission = 'can_restrict_members'
        
    has_perm, error_msg = await check_admin_permission(update, context, permission)
    if not has_perm:
        return await query.answer(error_msg, show_alert=True)
    
    # Bot permission check
    has_bot_perm, bot_error_msg = await check_bot_permission(update, context, permission)
    if not has_bot_perm:
        return await query.answer(bot_error_msg, show_alert=True)
    
    if answer == "no":
        return await query.message.edit_text(f"❌ `{cmd}` canceled.", parse_mode='HTML')
    
    await query.message.edit_text(f"⏳ `{cmd}` in progress…", parse_mode='HTML')
    
    try:
        if cmd == "kickall":
            await do_kickall(context.bot, chat_id, query.message)
        elif cmd == "banall":
            await do_banall(context.bot, chat_id, query.message)
        elif cmd in ["unbanall", "unabnall"]:
            await do_unbanall(context.bot, chat_id, query.message)
        elif cmd == "muteall":
            await do_muteall(context.bot, chat_id, query.message)
        elif cmd == "unmuteall":
            await do_unmuteall(context.bot, chat_id, query.message)
        elif cmd == "unpinall":
            await do_unpinall(context.bot, chat_id, query.message)
    except Exception as e:
        await query.message.edit_text(f"❌ Error during `{cmd}`:\n{str(e)}", parse_mode='HTML')

async def _get_chat_members(chat_id):
    """Fetch chat members via Telethon user session if available."""
    members = []
    try:
        import voice_chat
        tele = getattr(voice_chat, "telethon_client", None)
        if tele:
            if not tele.is_connected():
                try:
                    await tele.connect()
                except Exception:
                    pass
            if tele.is_connected():
                clean_id = int(str(chat_id).replace('-100', ''))
                try:
                    entity = await tele.get_entity(clean_id)
                except Exception:
                    entity = await tele.get_entity(chat_id)
                async for p in tele.iter_participants(entity):
                    members.append(p)
    except Exception as e:
        logging.warning(f"Error fetching members via Telethon for {chat_id}: {e}")
    return members

async def do_kickall(bot, chat_id, status_message=None):
    """Kick all non-admin members."""
    kicked, errors = 0, 0
    members = await _get_chat_members(chat_id)
    if not members:
        msg = "❌ Unable to fetch group member list. Ensure the Voice Monitor (Telethon session) is connected."
        if status_message:
            return await status_message.edit_text(msg)
        return await bot.send_message(chat_id, msg)

    for member in members:
        if getattr(member, 'bot', False):
            continue
        try:
            cm = await bot.get_chat_member(chat_id, member.id)
            if cm.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                continue
            await bot.ban_chat_member(chat_id, member.id)
            await asyncio.sleep(0.05)
            await bot.unban_chat_member(chat_id, member.id)
            kicked += 1
        except Exception:
            errors += 1
        await asyncio.sleep(0.05)

    msg = f"✅ <b>Kick All Completed</b>\n\nKicked: <b>{kicked}</b>\nFailures: <b>{errors}</b>"
    if status_message:
        await status_message.edit_text(msg, parse_mode='HTML')
    else:
        await bot.send_message(chat_id, msg, parse_mode='HTML')

async def do_banall(bot, chat_id, status_message=None):
    """Ban all non-admin members."""
    banned, errors = 0, 0
    members = await _get_chat_members(chat_id)
    if not members:
        msg = "❌ Unable to fetch group member list. Ensure the Voice Monitor (Telethon session) is connected."
        if status_message:
            return await status_message.edit_text(msg)
        return await bot.send_message(chat_id, msg)

    for member in members:
        if getattr(member, 'bot', False):
            continue
        try:
            cm = await bot.get_chat_member(chat_id, member.id)
            if cm.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                continue
            await bot.ban_chat_member(chat_id, member.id)
            banned += 1
        except Exception:
            errors += 1
        await asyncio.sleep(0.05)

    msg = f"✅ <b>Ban All Completed</b>\n\nBanned: <b>{banned}</b>\nFailures: <b>{errors}</b>"
    if status_message:
        await status_message.edit_text(msg, parse_mode='HTML')
    else:
        await bot.send_message(chat_id, msg, parse_mode='HTML')

async def do_unbanall(bot, chat_id, status_message=None):
    """Unban all banned members."""
    unbanned, errors = 0, 0
    banned_user_ids = set()

    # 1. Fetch banned participants via Telethon (MTProto ChannelParticipantsKicked)
    try:
        import voice_chat
        tele = getattr(voice_chat, "telethon_client", None)
        if tele:
            if not tele.is_connected():
                try:
                    await tele.connect()
                except Exception as ce:
                    logging.warning(f"Could not connect telethon_client: {ce}")

            if tele.is_connected():
                try:
                    clean_id = int(str(chat_id).replace('-100', ''))
                    try:
                        entity = await tele.get_entity(clean_id)
                    except Exception:
                        entity = await tele.get_entity(chat_id)

                    from telethon.tl.types import ChannelParticipantsKicked
                    async for p in tele.iter_participants(entity, filter=ChannelParticipantsKicked):
                        if getattr(p, 'id', None):
                            banned_user_ids.add(p.id)
                except Exception as te:
                    logging.warning(f"Telethon iter_participants error for {chat_id}: {te}")
    except Exception as e:
        logging.warning(f"Telethon client unavailable for do_unbanall: {e}")

    # 2. Check MongoDB moderation collection for recorded banned users
    try:
        from database import get_collection, COLLECTIONS
        moderation_col = get_collection(COLLECTIONS.get("moderation", "moderation"))
        if moderation_col is not None:
            mod_doc = moderation_col.find_one({"chat_id": str(chat_id)})
            if mod_doc and "banned_users" in mod_doc and isinstance(mod_doc["banned_users"], list):
                for uid in mod_doc["banned_users"]:
                    try:
                        banned_user_ids.add(int(uid))
                    except (ValueError, TypeError):
                        pass
    except Exception as me:
        logging.warning(f"MongoDB banned_users check error: {me}")

    # 3. Check and unban banned sender chats (channels)
    try:
        from moderation_manager_mongo import get_all_banned_channels, remove_banned_channel
        banned_channels = get_all_banned_channels(chat_id)
        if banned_channels:
            for ch in banned_channels:
                ch_id = ch.get("channel_id")
                if ch_id:
                    try:
                        await bot.unban_chat_sender_chat(chat_id, ch_id)
                        remove_banned_channel(chat_id, ch_id)
                        unbanned += 1
                    except Exception:
                        errors += 1
    except Exception as ce:
        logging.warning(f"Banned channels unban error: {ce}")

    # 4. Perform unbans for all discovered user IDs
    if banned_user_ids:
        total = len(banned_user_ids)
        last_edit = asyncio.get_event_loop().time()

        for idx, uid in enumerate(banned_user_ids, 1):
            try:
                await bot.unban_chat_member(chat_id, uid, only_if_banned=False)
                unbanned += 1
            except Exception as e:
                err_str = str(e).lower()
                if "flood" in err_str or "retry after" in err_str:
                    await asyncio.sleep(2)
                    try:
                        await bot.unban_chat_member(chat_id, uid, only_if_banned=False)
                        unbanned += 1
                    except Exception:
                        errors += 1
                else:
                    errors += 1

            now = asyncio.get_event_loop().time()
            if status_message and (now - last_edit > 3.0 or idx == total):
                try:
                    await status_message.edit_text(
                        f"⏳ <b>Unbanning in progress…</b>\n"
                        f"Progress: {idx}/{total}\n"
                        f"Unbanned: {unbanned} | Errors: {errors}",
                        parse_mode='HTML'
                    )
                    last_edit = now
                except Exception:
                    pass

            await asyncio.sleep(0.05)

    # 5. Clear MongoDB record for this chat if present
    try:
        from database import get_collection, COLLECTIONS
        moderation_col = get_collection(COLLECTIONS.get("moderation", "moderation"))
        if moderation_col is not None:
            moderation_col.update_one({"chat_id": str(chat_id)}, {"$set": {"banned_users": []}})
    except Exception:
        pass

    # 6. Format and send summary
    if unbanned == 0 and not banned_user_ids:
        summary = "ℹ️ No banned members found to unban."
    else:
        summary = (
            f"✅ <b>Mass Unban Complete</b>\n\n"
            f"🎉 <b>Unbanned:</b> {unbanned}\n"
            f"⚠️ <b>Failures / Skipped:</b> {errors}"
        )

    if status_message:
        try:
            await status_message.edit_text(summary, parse_mode='HTML')
        except Exception:
            await bot.send_message(chat_id, summary, parse_mode='HTML')
    else:
        await bot.send_message(chat_id, summary, parse_mode='HTML')

async def do_muteall(bot, chat_id, status_message=None):
    """Mute all non-admin members."""
    muted, errors = 0, 0
    permissions = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_polls=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False,
        can_invite_users=False,
    )
    members = await _get_chat_members(chat_id)
    if not members:
        msg = "❌ Unable to fetch group member list. Ensure the Voice Monitor (Telethon session) is connected."
        if status_message:
            return await status_message.edit_text(msg)
        return await bot.send_message(chat_id, msg)

    for member in members:
        if getattr(member, 'bot', False):
            continue
        try:
            cm = await bot.get_chat_member(chat_id, member.id)
            if cm.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                continue
            await bot.restrict_chat_member(chat_id, member.id, permissions)
            muted += 1
        except Exception:
            errors += 1
        await asyncio.sleep(0.05)

    msg = f"✅ <b>Mute All Completed</b>\n\nMuted: <b>{muted}</b>\nFailures: <b>{errors}</b>"
    if status_message:
        await status_message.edit_text(msg, parse_mode='HTML')
    else:
        await bot.send_message(chat_id, msg, parse_mode='HTML')

async def do_unmuteall(bot, chat_id, status_message=None):
    """Unmute all muted members."""
    unmuted, errors = 0, 0
    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_invite_users=True,
    )
    members = await _get_chat_members(chat_id)
    if not members:
        msg = "❌ Unable to fetch group member list. Ensure the Voice Monitor (Telethon session) is connected."
        if status_message:
            return await status_message.edit_text(msg)
        return await bot.send_message(chat_id, msg)

    for member in members:
        if getattr(member, 'bot', False):
            continue
        try:
            cm = await bot.get_chat_member(chat_id, member.id)
            if cm.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                continue
            await bot.restrict_chat_member(chat_id, member.id, permissions)
            unmuted += 1
        except Exception:
            errors += 1
        await asyncio.sleep(0.05)

    msg = f"✅ <b>Unmute All Completed</b>\n\nUnmuted: <b>{unmuted}</b>\nFailures: <b>{errors}</b>"
    if status_message:
        await status_message.edit_text(msg, parse_mode='HTML')
    else:
        await bot.send_message(chat_id, msg, parse_mode='HTML')

async def do_unpinall(bot, chat_id, status_message=None):
    """Unpin all messages."""
    try:
        await bot.unpin_all_chat_messages(chat_id)
        msg = "✅ Unpinned all messages."
    except Exception as e:
        msg = f"❌ Failed to unpin messages:\n{str(e)}"

    if status_message:
        await status_message.edit_text(msg, parse_mode='HTML')
    else:
        await bot.send_message(chat_id, msg, parse_mode='HTML')

def get_mass_actions_handlers():
    """Return mass actions handlers."""
    handlers = []
    for cmd in MASS_CMDS:
        handlers.append(CommandHandler(cmd, ask_mass_confirm))
    
    handlers.append(CallbackQueryHandler(
        handle_mass_confirm,
        pattern=r'^(kickall|banall|unbanall|unabnall|muteall|unmuteall|unpinall)_(yes|no)$'
    ))
    return handlers
