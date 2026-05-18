import asyncio
import logging
import os
from database import connect_to_mongodb, get_collection, COLLECTIONS
from config import OWNER_ID

# Configure logging
logging.basicConfig(level=logging.INFO)

async def check_user(user_id):
    if not connect_to_mongodb():
        print("Failed to connect to MongoDB")
        return

    print(f"--- Checking user {user_id} ---")
    
    # Check if Owner
    if user_id == OWNER_ID:
        print(f"User {user_id} is the BOT OWNER (OWNER_ID: {OWNER_ID})")
    else:
        print(f"User {user_id} is NOT the bot owner (OWNER_ID: {OWNER_ID})")

    # Check in users collection
    users_col = get_collection(COLLECTIONS["users"])
    user_doc = users_col.find_one({"id": user_id})
    if user_doc:
        print(f"Found in 'users' collection:")
        for k, v in user_doc.items():
            print(f"  {k}: {v}")
    else:
        print(f"Not found in 'users' collection")

    # Check in muters collection
    muters_col = get_collection(COLLECTIONS["muters"])
    muter_docs = list(muters_col.find({"user_id": user_id}))
    if muter_docs:
        print(f"Found in 'muters' collection (Total: {len(muter_docs)} chats):")
        for doc in muter_docs:
            print(f"  Chat ID: {doc.get('chat_id')}")
    else:
        print(f"Not found in 'muters' collection")

    # Check in voice_chat_managers collection
    vcm_col = get_collection(COLLECTIONS["voice_chat_managers"])
    vcm_docs = list(vcm_col.find({"user_id": user_id}))
    if vcm_docs:
        print(f"Found in 'voice_chat_managers' collection (Total: {len(vcm_docs)} chats):")
        for doc in vcm_docs:
            print(f"  Chat ID: {doc.get('chat_id')}")
    else:
        print(f"Not found in 'voice_chat_managers' collection")

    # Check in warns collection
    warns_col = get_collection(COLLECTIONS["warns"])
    warn_docs = list(warns_col.find({"user_id": user_id}))
    if warn_docs:
        print(f"Found in 'warns' collection (Total: {len(warn_docs)} chats):")
        for doc in warn_docs:
            print(f"  Chat ID: {doc.get('chat_id')}, Warns: {doc.get('warns')}")
    else:
        print(f"Not found in 'warns' collection")

if __name__ == "__main__":
    import sys
    user_id = 7814733300
    if len(sys.argv) > 1:
        try:
            user_id = int(sys.argv[1])
        except ValueError:
            pass
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(check_user(user_id))
