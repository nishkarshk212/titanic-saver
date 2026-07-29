#!/usr/bin/env python3
import logging
logging.basicConfig(level=logging.DEBUG)
print("Testing imports...")
try:
    from config import BOT_TOKEN, LOG_CHANNEL_ID, OWNER_ID
    print("✓ config imported")
except Exception as e:
    print(f"✗ config failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from database import connect_to_mongodb
    print("✓ database imported")
except Exception as e:
    print(f"✗ database failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from user_manager_mongo import cache_user_handler
    print("✓ user_manager_mongo imported")
except Exception as e:
    print(f"✗ user_manager_mongo failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from admin import get_admin_handlers
    print("✓ admin imported")
except Exception as e:
    print(f"✗ admin failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from welcome import get_welcome_handlers
    print("✓ welcome imported")
except Exception as e:
    print(f"✗ welcome failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from block_content import get_block_content_handlers
    print("✓ block_content imported")
except Exception as e:
    print(f"✗ block_content failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from clean_service import get_clean_service_handlers
    print("✓ clean_service imported")
except Exception as e:
    print(f"✗ clean_service failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from auto_delete import get_auto_delete_handlers
    print("✓ auto_delete imported")
except Exception as e:
    print(f"✗ auto_delete failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from moderation import get_moderation_handlers
    print("✓ moderation imported")
except Exception as e:
    print(f"✗ moderation failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from filter import get_filter_handlers
    print("✓ filter imported")
except Exception as e:
    print(f"✗ filter failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from bot_protection import get_bot_protection_handlers
    print("✓ bot_protection imported")
except Exception as e:
    print(f"✗ bot_protection failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from link_spam import get_link_spam_handlers
    print("✓ link_spam imported")
except Exception as e:
    print(f"✗ link_spam failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from forward_protection import get_forward_protection_handlers
    print("✓ forward_protection imported")
except Exception as e:
    print(f"✗ forward_protection failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from settings import get_settings_handlers
    print("✓ settings imported")
except Exception as e:
    print(f"✗ settings failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from help import get_help_handlers
    print("✓ help imported")
except Exception as e:
    print(f"✗ help failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from ai_chat import get_chatgpt_handlers
    print("✓ ai_chat imported")
except Exception as e:
    print(f"✗ ai_chat failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from translator import get_translation_handlers
    print("✓ translator imported")
except Exception as e:
    print(f"✗ translator failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from language_filter import get_language_handlers
    print("✓ language_filter imported")
except Exception as e:
    print(f"✗ language_filter failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from sticker_manager import get_sticker_handlers
    print("✓ sticker_manager imported")
except Exception as e:
    print(f"✗ sticker_manager failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from blocking_handler import get_blocking_handlers, get_blocking_command_handlers
    print("✓ blocking_handler imported")
except Exception as e:
    print(f"✗ blocking_handler failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from edit_handler import get_edit_handlers
    print("✓ edit_handler imported")
except Exception as e:
    print(f"✗ edit_handler failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from bio_handler import get_bio_handlers
    print("✓ bio_handler imported")
except Exception as e:
    print(f"✗ bio_handler failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from antiflood import get_antiflood_handlers
    print("✓ antiflood imported")
except Exception as e:
    print(f"✗ antiflood failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from nightmode import get_nightmode_handlers
    print("✓ nightmode imported")
except Exception as e:
    print(f"✗ nightmode failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from recurring import get_recurring_handlers
    print("✓ recurring imported")
except Exception as e:
    print(f"✗ recurring failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from Manager import get_manager_handlers
    print("✓ Manager imported")
except Exception as e:
    print(f"✗ Manager failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from tagger import get_tagger_handlers
    print("✓ tagger imported")
except Exception as e:
    print(f"✗ tagger failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from voice_chat import get_voice_chat_handlers
    print("✓ voice_chat imported")
except Exception as e:
    print(f"✗ voice_chat failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from join_request import get_join_request_handlers
    print("✓ join_request imported")
except Exception as e:
    print(f"✗ join_request failed: {e}")
    import traceback
    traceback.print_exc()

print("All imports tested!")
