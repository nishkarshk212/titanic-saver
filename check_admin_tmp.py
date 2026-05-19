import os
import sys
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI") or "mongodb+srv://mybotpanda_db_user:hx0n5AI90lFGyl93@grouphelp.puxyti8.mongodb.net/?appName=GROUPHELP"
DATABASE_NAME = "GROUPHELP"
TARGET_USER_ID = 8728532487

def check_user():
    try:
        client = MongoClient(MONGODB_URI, tls=True, tlsCAFile=certifi.where())
        db = client[DATABASE_NAME]
        admins_col = db["admins"]
        
        results = list(admins_col.find({"user_id": TARGET_USER_ID}))
        
        if not results:
            print(f"User {TARGET_USER_ID} is not found in the admin database.")
            return

        print(f"Found {len(results)} admin records for User {TARGET_USER_ID}:")
        for doc in results:
            chat_id = doc.get("chat_id")
            perms = doc.get("permissions", {})
            print(f"\n--- Chat ID: {chat_id} ---")
            for p, val in perms.items():
                status = "✅" if val else "❌"
                print(f"{p}: {status}")
            print(f"Last Updated: {doc.get('last_updated')}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_user()
