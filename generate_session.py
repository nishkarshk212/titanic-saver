#!/usr/bin/env python3
"""
Generate Telethon Session String for Premium Account
Run this script and follow the prompts
"""
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import sys

def main():
    print("=" * 60)
    print("🔑 Telegram Session String Generator")
    print("=" * 60)
    print()
    
    # Get API credentials
    api_id = input("Enter your API ID (from my.telegram.org): ").strip()
    api_hash = input("Enter your API Hash (from my.telegram.org): ").strip()
    
    if not api_id or not api_hash:
        print("❌ API ID and API Hash are required!")
        sys.exit(1)
    
    print()
    print("📱 Connecting to Telegram...")
    print()
    
    try:
        # Create client and connect
        with TelegramClient(StringSession(), int(api_id), api_hash) as client:
            # You'll be prompted to enter phone number and code
            me = client.get_me()
            
            print()
            print("=" * 60)
            print("✅ Successfully connected!")
            print("=" * 60)
            print()
            print(f"👤 Name: {me.first_name} {me.last_name or ''}")
            print(f"📱 Username: @{me.username or 'Not set'}")
            print(f"⭐ Premium: {me.premium}")
            print(f"🆔 User ID: {me.id}")
            print()
            print("=" * 60)
            print("📋 YOUR SESSION STRING:")
            print("=" * 60)
            print()
            session_string = client.session.save()
            print(session_string)
            print()
            print("=" * 60)
            print("⚠️  COPY THIS STRING AND KEEP IT SECRET!")
            print("=" * 60)
            print()
            print("Add this to your .env file:")
            print(f"TELEGRAM_API_ID={api_id}")
            print(f"TELEGRAM_API_HASH={api_hash}")
            print(f"PREMIUM_SESSION_STRING={session_string}")
            print(f"OWNER_ID={me.id}")
            print()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. API ID and Hash are correct")
        print("  2. You're entering the correct phone number")
        print("  3. You're entering the login code from Telegram")
        sys.exit(1)

if __name__ == '__main__':
    main()
