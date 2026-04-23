#!/bin/bash

# Database Statistics and Zombie Check Script
# Run this on the server: bash check_stats.sh

echo "========================================="
echo "  📊 Database & Server Statistics"
echo "========================================="
echo ""

# Check if MongoDB is running
echo "🔍 Checking MongoDB status..."
MONGO_STATUS=$(systemctl is-active mongod 2>/dev/null)

if [ "$MONGO_STATUS" != "active" ]; then
    echo "⚠️  MongoDB is not running. Starting..."
    systemctl start mongod
    sleep 2
fi

# Check MongoDB status again
MONGO_STATUS=$(systemctl is-active mongod 2>/dev/null)
if [ "$MONGO_STATUS" == "active" ]; then
    echo "✅ MongoDB is running!"
    echo ""
    
    # Get database stats
    echo "📈 Database Statistics:"
    echo "-----------------------------------------"
    
    mongosh --quiet --eval "
        use GROUPHELP;
        
        // Get collections info
        const collections = db.getCollectionNames();
        print('📁 Collections: ' + collections.length);
        print('');
        
        // Users collection
        const usersCount = db.users.countDocuments();
        print('👥 Total Cached Users: ' + usersCount);
        
        // Settings collection (groups)
        const groupsCount = db.settings.countDocuments();
        print('👥 Total Groups: ' + groupsCount);
        
        // Moderation collection
        const modCount = db.moderation.countDocuments();
        print('📝 Moderation Records: ' + modCount);
        
        // Count banned users across all groups
        let totalBanned = 0;
        db.moderation.find({banned_users: {\$exists: true}}).forEach(function(doc) {
            if (doc.banned_users && Array.isArray(doc.banned_users)) {
                totalBanned += doc.banned_users.length;
            }
        });
        print('🔨 Total Banned Users (all groups): ' + totalBanned);
        
        // Count muted users
        let totalMuted = 0;
        db.moderation.find({muted_users: {\$exists: true}}).forEach(function(doc) {
            if (doc.muted_users && Array.isArray(doc.muted_users)) {
                totalMuted += doc.muted_users.length;
            }
        });
        print('🔇 Total Muted Users (all groups): ' + totalMuted);
        
        // Count warned users
        let totalWarned = 0;
        db.moderation.find({warned_users: {\$exists: true}}).forEach(function(doc) {
            if (doc.warned_users && Array.isArray(doc.warned_users)) {
                totalWarned += doc.warned_users.length;
            }
        });
        print('⚠️  Total Warned Users (all groups): ' + totalWarned);
        
        print('');
        print('=========================================');
    " 2>/dev/null
    
    echo ""
    echo "🧹 Zombie/Deleted Accounts Check:"
    echo "-----------------------------------------"
    echo "To check for deleted accounts in a specific group:"
    echo "  • Use /zombies command in that group"
    echo "  • The bot will scan and list all deleted accounts"
    echo "  • You can then remove them with /zombies clean"
    echo ""
    
else
    echo "❌ MongoDB failed to start!"
    echo "Check logs: journalctl -u mongod -n 50"
fi

echo ""
echo "📋 Server Resources:"
echo "-----------------------------------------"
echo "🖥️  CPU Usage:"
top -bn1 | grep "Cpu(s)" | awk '{print "   " $2 "% used"}'
echo ""
echo "💾 Memory Usage:"
free -h | grep Mem | awk '{print "   Used: " $3 " / Total: " $2 " (" int($3/$2*100) "%)"}'
echo ""
echo "💿 Disk Usage:"
df -h / | tail -1 | awk '{print "   Used: " $3 " / Total: " $2 " (" $5 ")"}'
echo ""

echo "========================================="
echo "  ✅ Check Complete!"
echo "========================================="
