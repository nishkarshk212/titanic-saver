# Command Permissions Feature - Quick Reference

## What Was Added

### 1. New Settings Panel Button
- **Location**: Main settings menu
- **Button**: "🎛️ Command Perms"
- **Purpose**: Configure individual command access levels

### 2. Three Access Levels
- **All** - Everyone can use the command
- **Admin** - Only admins can use the command  
- **Owner** - Only group creator can use the command

### 3. Configurable Commands (22 total)

**Basic Commands:**
- start, help, id, info, report

**Moderation Commands:**
- ban, unban, mute, unmute, warn, unwarn, kick

**Management Commands:**
- purge, pin, unpin, promote, demote

**Info & Utilities:**
- staff, bots, zombies, sg

**Mass Actions:**
- mass_actions

**Settings:**
- settings

### 4. Files Modified

1. **settings_manager_mongo.py**
   - Added 22 new settings keys for command access
   - Added `check_command_access()` helper function

2. **settings.py**
   - Added "🎛️ Command Perms" button to main menu
   - Created `get_command_permissions_keyboard()` function
   - Added view handler for command permissions
   - Added toggle handler for individual commands
   - Updated settings command to use new permission check

3. **bot.py**
   - Updated `/info` command to use new permission system
   - Updated `/id` command to use new permission system

4. **help.py**
   - Updated `/help` command to use new permission system

### 5. How It Works

**User Flow:**
1. User types `/settings`
2. Clicks "🎛️ Command Perms"
3. Sees categorized list of commands
4. Taps any command to cycle: All → Admin → Owner → All
5. Changes save automatically

**Permission Check:**
```python
if not await check_command_access(chat_id, user_id, 'command_name', context):
    # Deny access
```

### 6. Default Configuration

**All Members Can Use:**
- /start, /help, /id, /info, /report
- /staff, /bots, /sg

**Admins Only:**
- /settings, /ban, /unban, /mute, /unmute
- /warn, /unwarn, /kick, /purge, /pin, /unpin
- /promote, /demote, /zombies, mass actions

### 7. Key Features

✅ Granular per-command control
✅ Cyclic toggling (All → Admin → Owner)
✅ Categorized command list
✅ Owner always has access
✅ Backwards compatible
✅ Instant effect (no restart needed)
✅ Per-group settings
✅ MongoDB storage

### 8. Testing the Feature

1. Start the bot
2. Add to a group
3. Type `/settings`
4. Click "🎛️ Command Perms"
5. Tap any command button to change its access
6. Try using the command with different user roles

### 9. Adding More Commands

To add a new command to the permission system:

1. Add to `DEFAULT_CHAT_SETTINGS`:
   ```python
   "cmd_access_yourcommand": "admin"
   ```

2. Add to `get_command_permissions_keyboard()`:
   ```python
   ("YourCommand", "cmd_access_yourcommand")
   ```

3. Update your command handler:
   ```python
   if not await check_command_access(chat_id, user_id, 'yourcommand', context):
       return
   ```

### 10. Benefits

- **Flexibility**: Fine-tune who can use what
- **Security**: Prevent unauthorized command usage
- **Control**: Owner-level restrictions for sensitive commands
- **User-Friendly**: Easy-to-use interface
- **Scalable**: Easy to add more commands
