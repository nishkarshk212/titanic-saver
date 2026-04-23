"""
Manager Module - Group Management Commands
Ported from AnnieXMusic to python-telegram-bot

This module contains:
- actions.py: Ban, unban, mute, unmute, kick, etc.
- grouphandler.py: Pin, unpin, set photo/title/description
- id.py: Get user/chat/message IDs
- info.py: User information
- mass_actions.py: Kickall, banall, muteall, etc.
- promote.py: Promote, demote, tempadmin
- purge.py: Delete messages in bulk
- staff.py: List admins and bots
- sg.py: Sangmata username history checker
- zombie.py: Clean deleted accounts
"""

from Manager.actions import get_manager_actions_handlers
from Manager.grouphandler import get_grouphandler_handlers
from Manager.id import get_id_handlers
from Manager.info import get_info_handlers
from Manager.mass_actions import get_mass_actions_handlers
from Manager.promote import get_promote_handlers
from Manager.purge import get_purge_handlers
from Manager.staff import get_staff_handlers
from Manager.sg import get_sg_handlers
from Manager.zombie import get_zombie_handlers

def get_manager_handlers():
    """Return all Manager handlers."""
    handlers = []
    handlers.extend(get_manager_actions_handlers())
    handlers.extend(get_grouphandler_handlers())
    handlers.extend(get_id_handlers())
    handlers.extend(get_info_handlers())
    handlers.extend(get_mass_actions_handlers())
    handlers.extend(get_promote_handlers())
    handlers.extend(get_purge_handlers())
    handlers.extend(get_staff_handlers())
    handlers.extend(get_sg_handlers())
    handlers.extend(get_zombie_handlers())
    
    return handlers

__all__ = [
    'get_manager_handlers',
    'get_manager_actions_handlers',
    'get_grouphandler_handlers',
    'get_id_handlers',
    'get_info_handlers',
    'get_mass_actions_handlers',
    'get_promote_handlers',
    'get_purge_handlers',
    'get_staff_handlers',
    'get_sg_handlers',
    'get_zombie_handlers',
]
