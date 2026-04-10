# MongoDB Setup Guide

## Overview
Your Telegram bot has been successfully integrated with MongoDB for persistent, scalable data storage. All data that was previously stored in JSON files is now stored in a MongoDB Atlas cluster.

## What's Been Created

### New Files
1. **database.py** - MongoDB connection and configuration
2. **user_manager_mongo.py** - User data management with MongoDB
3. **settings_manager_mongo.py** - Chat settings management with MongoDB
4. **moderation_manager_mongo.py** - Moderation data (warns, muters, banned channels) with MongoDB
5. **filters_manager_mongo.py** - Filter management with MongoDB
6. **block_content_manager_mongo.py** - Blocked content management with MongoDB
7. **migrate_to_mongodb.py** - Migration script to transfer JSON data to MongoDB

### MongoDB Collections
The following collections have been created in your MongoDB database:

- **users** - User cache and statistics
- **chat_settings** - Group-specific settings
- **warns** - User warning counts per group
- **muters** - Users with mute permissions
- **voice_chat_managers** - Users with voice chat management permissions
- **banned_channels** - Banned channels per group
- **blocked_content** - Blocked text and media per group
- **filters** - Custom filters per group

## MongoDB Connection

Your MongoDB connection string is configured in `database.py`:
```
mongodb+srv://mybotpanda_db_user:hx0n5AI90lFGyl93@grouphelp.puxyti8.mongodb.net/?appName=GROUPHELP
```

**Database Name:** `GROUPHELP`

## Migration from JSON to MongoDB

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run Migration Script
```bash
python migrate_to_mongodb.py
```

This will:
- Connect to your MongoDB cluster
- Create all necessary collections and indexes
- Transfer all data from JSON files to MongoDB
- Show migration progress and results

### Step 3: Verify Migration
After running the migration script, you should see output like:
```
✅ Migrated X users to MongoDB
✅ Migrated X chat settings to MongoDB
✅ Migrated X warn records to MongoDB
...
```

### Step 4: Start Your Bot
```bash
python bot.py
```

The bot will automatically:
1. Connect to MongoDB on startup
2. Initialize collections and indexes
3. Use MongoDB for all data operations

## Benefits of MongoDB

✅ **Persistent Storage** - Data won't be lost on bot restart
✅ **Scalability** - Can handle millions of records efficiently
✅ **Performance** - Fast queries with proper indexing
✅ **Reliability** - Automatic backups and replication
✅ **Concurrent Access** - Multiple bot instances can run safely
✅ **Real-time Updates** - No file locking issues

## Database Indexes

Automatic indexes have been created for optimal performance:

- **users**: `id` (unique), `username`
- **chat_settings**: `chat_id` (unique)
- **warns**: `chat_id + user_id` (unique compound index)
- **muters**: `chat_id + user_id` (unique compound index)
- **voice_chat_managers**: `chat_id + user_id` (unique compound index)
- **banned_channels**: `chat_id + channel_id` (unique compound index)
- **blocked_content**: `chat_id`
- **filters**: `chat_id + trigger` (unique compound index)

## Monitoring Your Database

You can monitor your MongoDB usage and data through:
1. **MongoDB Atlas Dashboard**: https://cloud.mongodb.com/
2. **MongoDB Compass**: GUI tool for database exploration

## Backup and Recovery

MongoDB Atlas provides automatic backups:
- Daily backups
- Point-in-time recovery
- Cross-region replication (on higher tiers)

## Troubleshooting

### Connection Issues
If you see "Failed to connect to MongoDB":
1. Check your internet connection
2. Verify the MongoDB URI in `database.py`
3. Ensure your IP is whitelisted in MongoDB Atlas
4. Check MongoDB Atlas cluster status

### Migration Fails
If migration fails:
1. Check the error message in the console
2. Verify JSON files exist and are valid
3. Ensure MongoDB connection is working
4. Run migration script again (it's idempotent)

### Bot Starts but Data Missing
If the bot starts but data seems missing:
1. Run the migration script: `python migrate_to_mongodb.py`
2. Check MongoDB Atlas to verify data was migrated
3. Check bot logs for any errors

## Environment Variables (Optional)

You can move the MongoDB URI to `.env` file for better security:

1. Add to `.env`:
```
MONGODB_URI=mongodb+srv://mybotpanda_db_user:hx0n5AI90lFGyl93@grouphelp.puxyti8.mongodb.net/?appName=GROUPHELP
```

2. The `database.py` file will automatically use the environment variable

## Security Notes

⚠️ **Important**: Your MongoDB credentials are currently in the code. For production:
1. Move `MONGODB_URI` to `.env` file
2. Add `.env` to `.gitignore`
3. Never commit credentials to version control
4. Restrict IP access in MongoDB Atlas

## Support

If you encounter any issues:
1. Check the bot console logs
2. Check MongoDB Atlas logs
3. Verify all dependencies are installed
4. Ensure MongoDB cluster is running

## Next Steps

1. ✅ Run the migration script
2. ✅ Test the bot functionality
3. ✅ Verify data in MongoDB Atlas
4. ✅ Monitor performance
5. ✅ Set up automated backups (if needed)

---

**Your bot is now powered by MongoDB! 🚀**
