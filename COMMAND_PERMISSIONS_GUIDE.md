# Command Permissions Guide

## Overview
The Command Permissions feature allows you to control who can use each bot command in your group. You can set access levels for individual commands, giving you granular control over bot functionality.

## Access Levels
Each command can be set to one of three access levels:

1. **All** - Every member in the group can use the command
2. **Admin** - Only group administrators can use the command
3. **Owner** - Only the group creator/owner can use the command

## How to Configure Command Permissions

### Accessing Command Permissions
1. Use `/settings` or `/config` in your group
2. Click on **"🎛️ Command Perms"** button
3. You'll see a categorized list of all commands with their current access levels

### Changing Command Access
1. In the Command Permissions panel, tap on any command button
2. Each tap cycles through the access levels: **All → Admin → Owner → All**
3. The button will update to show the new access level
4. Changes are saved automatically

## Command Categories

### 📖 Basic Commands
- `/start` - Bot introduction
- `/help` - Help menu
- `/id` - Show user/chat ID
- `/info` - User information
- `/report` - Report a message to admins

### 🛡️ Moderation Commands
- `/ban` - Ban a user
- `/unban` - Unban a user
- `/mute` - Mute a user
- `/unmute` - Unmute a user
- `/warn` - Warn a user
- `/unwarn` - Remove warns
- `/kick` - Kick a user

### 👥 Management Commands
- `/purge` - Delete messages in bulk
- `/pin` - Pin a message
- `/unpin` - Unpin a message
- `/promote` - Promote user to admin
- `/demote` - Demote admin to member

### 📋 Info & Utilities
- `/staff` - List all admins
- `/bots` - List all bots
- `/zombies` - Clean deleted accounts
- `/sg` - Check username history

### ⚠️ Mass Actions
- Mass Actions (kickall, banall, muteall, etc.)

### ⚙️ Settings
- `/settings` or `/config` - Bot settings panel

## Default Settings

By default, commands are set as follows:

**Accessible to All:**
- `/start`, `/help`, `/id`, `/info`, `/report`
- `/staff`, `/bots`, `/sg`

**Admin Only:**
- `/settings`, `/ban`, `/unban`, `/mute`, `/unmute`
- `/warn`, `/unwarn`, `/kick`, `/purge`, `/pin`, `/unpin`
- `/promote`, `/demote`, `/zombies`, Mass Actions

## Important Notes

1. **Owner Override**: The group owner/creator can always use all commands, regardless of settings
2. **Admin Rights**: For admin-only commands, users must be actual admins (not just have the role)
3. **Backwards Compatible**: The old "Command Access" setting (all/admins toggle) still works for basic commands
4. **Per-Group Settings**: Command permissions are configured separately for each group
5. **Instant Effect**: Changes take effect immediately - no bot restart needed

## Use Cases

### Example 1: Strict Moderation
Only admins can use moderation tools:
- Set all moderation commands to **Admin**
- Keep basic commands like `/help` and `/id` as **All**

### Example 2: Owner-Controlled Group
Only owner can perform sensitive actions:
- Set `/ban`, `/promote`, mass actions to **Owner**
- Set `/mute`, `/warn` to **Admin**
- Set `/help`, `/id` to **All**

### Example 3: Community-Driven Group
Allow members to use some moderation:
- Set `/report` to **All**
- Set `/info` to **All**
- Keep `/ban`, `/promote` as **Admin**

## Technical Implementation

### Database Storage
Command permissions are stored in MongoDB with keys like:
- `cmd_access_ban`
- `cmd_access_help`
- `cmd_access_settings`
- etc.

### Checking Permissions in Code
```python
from settings_manager_mongo import check_command_access

async def your_command(update, context):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if not await check_command_access(chat_id, user_id, 'command_name', context):
        await send_bot_response(update, context, "You don't have permission to use this command.")
        return
    
    # Your command logic here
```

## Troubleshooting

**Command not working after changing permissions?**
- Check the current access level in settings
- Verify your role in the group (member/admin/owner)
- Ensure the bot has proper admin rights

**Can't access settings?**
- You need both "Change Group Info" and "Ban Users" permissions
- Or be the group owner

**Want to reset to defaults?**
- Manually cycle through each command back to desired setting
- Or delete the group's settings from MongoDB (advanced)

## Future Enhancements
- Custom roles (e.g., "Moderator" role)
- Time-based access (e.g., admin only during certain hours)
- Command usage statistics
- Import/export permission presets
