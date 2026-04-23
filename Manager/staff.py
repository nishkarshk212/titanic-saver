"""
Manager Staff - List admins and bots
Ported from AnnieXMusic to python-telegram-bot
"""

import html
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ChatMemberStatus

def mention_html(user):
    """Create HTML mention."""
    name = html.escape((user.first_name or "User").strip())
    return f'<a href="tg://user?id={user.id}">{name}</a>'

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all admins in the group."""
    chat = update.effective_chat
    
    if chat.type not in ['group', 'supergroup']:
        return await update.message.reply_text("⚠️ <i>Use this in a group or supergroup.</i>", parse_mode='HTML')
    
    try:
        owners = []
        human_admins = []
        bot_admins = []
        
        async for member in context.bot.get_chat_members(chat.id):
            if member.status in ['administrator', 'creator']:
                if hasattr(member, 'privileges') and getattr(member.privileges, 'is_anonymous', False):
                    continue
                
                user = member.user
                if member.status == 'creator':
                    owners.append(user)
                else:
                    if user.is_bot:
                        bot_admins.append(user)
                    else:
                        human_admins.append(user)
        
        title = html.escape(chat.title or "this chat")
        txt = f"🛡 <b>Group Staff — {title}</b>\n\n"
        
        owner_line = mention_html(owners[0]) if owners else "<i>Hidden Owner</i>"
        txt += f"<b>Owner</b>\n└ {owner_line}\n\n"
        
        txt += "<b>👤 Admins</b>\n"
        if not human_admins:
            txt += "└ <i>No human admins</i>\n"
        else:
            for i, adm in enumerate(human_admins):
                branch = "└" if i == len(human_admins) - 1 else "├"
                handle = f"@{adm.username}" if adm.username else mention_html(adm)
                txt += f"{branch} {handle}\n"
        
        txt += "\n<b>🤖 Bot Admins</b>\n"
        if not bot_admins:
            txt += "└ <i>No bot admins</i>\n"
        else:
            for i, adm in enumerate(bot_admins):
                branch = "└" if i == len(bot_admins) - 1 else "├"
                handle = f"@{adm.username}" if adm.username else mention_html(adm)
                txt += f"{branch} {handle}\n"
        
        total = len(owners) + len(human_admins) + len(bot_admins)
        txt += f"\n<b>Total Admins:</b> {total}"
        
        await context.bot.send_message(chat.id, txt, parse_mode='HTML')
        
    except Exception as e:
        if 'ChatAdminRequired' in str(type(e)):
            await update.message.reply_text("❌ <i>I need admin rights to list admins here.</i>", parse_mode='HTML')

async def list_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all bots in the group."""
    chat = update.effective_chat
    
    if chat.type not in ['group', 'supergroup']:
        return await update.message.reply_text("⚠️ <i>Use this in a group or supergroup.</i>", parse_mode='HTML')
    
    try:
        bots = []
        
        async for member in context.bot.get_chat_members(chat.id):
            if member.user.is_bot:
                is_admin = member.status in ['administrator', 'creator']
                bots.append((member.user, is_admin))
        
        title = html.escape(chat.title or "this chat")
        txt = f"🤖 <b>Bot List — {title}</b>\n\n<b>Bots</b>\n"
        
        if not bots:
            txt += "└ <i>No bots found</i>\n"
        else:
            for i, (bt, is_admin) in enumerate(bots):
                branch = "└" if i == len(bots) - 1 else "├"
                handle = f"@{bt.username}" if bt.username else mention_html(bt)
                admin_flag = " <b>— Admin</b> 🛡" if is_admin else ""
                txt += f"{branch} {handle}{admin_flag}\n"
        
        txt += f"\n<b>Total Bots:</b> {len(bots)}"
        
        await context.bot.send_message(chat.id, txt, parse_mode='HTML')
        
    except Exception as e:
        if 'ChatAdminRequired' in str(type(e)):
            await update.message.reply_text("❌ <i>I need admin rights to list bots here.</i>", parse_mode='HTML')

def get_staff_handlers():
    """Return staff handlers."""
    return [
        CommandHandler(["admins", "staff"], list_admins),
        CommandHandler("bots", list_bots),
    ]
