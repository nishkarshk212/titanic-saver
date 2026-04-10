"""
Test script to verify MongoDB connection and basic operations.
"""

from database import connect_to_mongodb, initialize_collections, get_collection, COLLECTIONS
import datetime

def test_connection():
    """Test MongoDB connection."""
    print("=" * 60)
    print("🔌 Testing MongoDB Connection...")
    print("=" * 60)
    
    if connect_to_mongodb():
        print("✅ Successfully connected to MongoDB!")
        return True
    else:
        print("❌ Failed to connect to MongoDB")
        return False

def test_collections():
    """Test collection initialization."""
    print("\n" + "=" * 60)
    print("📦 Testing Collection Initialization...")
    print("=" * 60)
    
    if initialize_collections():
        print("✅ Collections initialized successfully!")
        return True
    else:
        print("❌ Failed to initialize collections")
        return False

def test_basic_operations():
    """Test basic CRUD operations."""
    print("\n" + "=" * 60)
    print("🧪 Testing Basic CRUD Operations...")
    print("=" * 60)
    
    try:
        # Test users collection
        users_col = get_collection(COLLECTIONS["users"])
        if users_col is None:
            print("❌ Failed to get users collection")
            return False
        
        # Insert test user
        test_user = {
            "id": 999999999,
            "name": "Test User",
            "username": "testuser",
            "joined_date": "2024-01-01",
            "msg_count": 0,
            "created_at": datetime.datetime.now(),
            "last_updated": datetime.datetime.now()
        }
        
        result = users_col.update_one(
            {"id": 999999999},
            {"$set": test_user},
            upsert=True
        )
        print(f"✅ Inserted/Updated test user (upserted: {result.upserted_id is not None})")
        
        # Read test user
        user = users_col.find_one({"id": 999999999})
        if user:
            print(f"✅ Retrieved test user: {user['name']}")
        else:
            print("❌ Failed to retrieve test user")
            return False
        
        # Update test user
        users_col.update_one(
            {"id": 999999999},
            {"$set": {"msg_count": 5}}
        )
        user = users_col.find_one({"id": 999999999})
        if user and user.get("msg_count") == 5:
            print(f"✅ Updated test user message count: {user['msg_count']}")
        else:
            print("❌ Failed to update test user")
            return False
        
        # Delete test user
        users_col.delete_one({"id": 999999999})
        user = users_col.find_one({"id": 999999999})
        if not user:
            print("✅ Deleted test user successfully")
        else:
            print("❌ Failed to delete test user")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error during CRUD operations: {e}")
        return False

def test_settings_collection():
    """Test settings collection."""
    print("\n" + "=" * 60)
    print("⚙️  Testing Settings Collection...")
    print("=" * 60)
    
    try:
        settings_col = get_collection(COLLECTIONS["settings"])
        if settings_col is None:
            print("❌ Failed to get settings collection")
            return False
        
        # Insert test settings
        test_settings = {
            "chat_id": "-999999999",
            "settings": {
                "welcome_enabled": True,
                "auto_delete_enabled": False,
                "warn_limit": 3
            },
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now()
        }
        
        settings_col.update_one(
            {"chat_id": "-999999999"},
            {"$set": test_settings},
            upsert=True
        )
        print("✅ Inserted test settings")
        
        # Read test settings
        settings = settings_col.find_one({"chat_id": "-999999999"})
        if settings:
            print(f"✅ Retrieved settings for chat: {settings['chat_id']}")
        else:
            print("❌ Failed to retrieve settings")
            return False
        
        # Clean up
        settings_col.delete_one({"chat_id": "-999999999"})
        print("✅ Cleaned up test settings")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing settings: {e}")
        return False

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🚀 MongoDB Connection Test Suite")
    print("=" * 60 + "\n")
    
    tests = [
        ("Connection Test", test_connection),
        ("Collection Initialization", test_collections),
        ("Basic CRUD Operations", test_basic_operations),
        ("Settings Collection", test_settings_collection),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("📊 Test Results")
    print("=" * 60)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    print("=" * 60)
    
    if failed == 0:
        print("\n🎉 All tests passed! MongoDB is ready to use!")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the errors above.")
    
    print()

if __name__ == "__main__":
    main()
