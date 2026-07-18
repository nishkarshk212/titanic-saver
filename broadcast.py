import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import Forbidden, BadRequest, RetryAfter

from config import OWNER_ID
from database import get_collection, get_all_chats, COLLECTIONS


def _get_all_user_ids():
    """Return every cached user id from MongoDB."""
    users_col = get_collection(COLLECTIONS["users"])
    if users_col is None:
        return []
    try:
        return [d["id"] for d in users_col.find({}, {"id": 1}) if d.get("id")]
    except Exception as e:
        logging.error(f"[BROADCAST] Failed to load users: {e}")
        return []


def _get_all_chat_ids():
    """Return every group chat id the bot knows about."""
    ids = []
    for doc in get_all_chats():
        cid = doc.get("chat_id")
        if cid:
            ids.append(cid)
    return ids


async def _deliver(bot, targets, source_msg):
    """Copy source_msg to each target; returns (sent, failed). Handles flood waits."""
    sent = failed = 0
    for tid in targets:
        try:
            await bot.copy_message(tid, source_msg.chat_id, source_msg.message_id)
            sent += 1
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
            try:
                await bot.copy_message(tid, source_msg.chat_id, source_msg.message_id)
                sent += 1
            except Exception:
                failed += 1
        except (Forbidden, BadRequest):
            failed += 1
        except Exception as e:
            logging.error(f"[BROADCAST] {tid}: {e}")
            failed += 1
        await asyncio.sleep(0.05)  # ~20 msgs/sec, well under Telegram limits
    return sent, failed


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner-only. Reply to a message with /broadcast to send it to all users.

    Flags: /broadcast chats  -> send to groups instead of users
           /broadcast all     -> send to both users and groups
    """
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        return

    msg = update.message.reply_to_message
    if not msg:
        await update.message.reply_text(
            "📢 <b>Broadcast</b>\n\n"
            "Reply to any message with:\n"
            "• <code>/broadcast</code> — send to all users\n"
            "• <code>/broadcast chats</code> — send to all groups\n"
            "• <code>/broadcast all</code> — send to users + groups",
            parse_mode="HTML",
        )
        return

    mode = (context.args[0].lower() if context.args else "users")
    if mode == "chats":
        targets, label = _get_all_chat_ids(), "groups"
    elif mode == "all":
        targets, label = _get_all_user_ids() + _get_all_chat_ids(), "users + groups"
    else:
        targets, label = _get_all_user_ids(), "users"

    targets = list(dict.fromkeys(targets))  # dedupe, preserve order
    if not targets:
        await update.message.reply_text("⚠️ No targets found.")
        return

    status = await update.message.reply_text(
        f"📢 Broadcasting to {len(targets)} {label}…", parse_mode="HTML"
    )
    sent, failed = await _deliver(context.bot, targets, msg)
    try:
        await status.edit_text(
            f"✅ <b>Broadcast complete</b>\n\n"
            f"• Target: {label}\n"
            f"• Sent: <code>{sent}</code>\n"
            f"• Failed: <code>{failed}</code>",
            parse_mode="HTML",
        )
    except Exception:
        pass


def get_broadcast_handlers():
    return [CommandHandler("broadcast", broadcast_command)]
