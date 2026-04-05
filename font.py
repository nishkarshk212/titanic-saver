import re

def to_small_caps(text):
    """Converts standard characters to small caps characters while preserving HTML tags."""
    normal_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    small_caps_chars = "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789"
    
    trans_table = str.maketrans(normal_chars, small_caps_chars)

    def replace_func(match):
        return match.group(0).translate(trans_table)

    # Regex to find everything EXCEPT HTML tags
    # This splits the text into parts that are HTML tags and parts that are not
    parts = re.split(r'(<[^>]+>)', text)
    result = []
    for part in parts:
        if part.startswith('<') and part.endswith('>'):
            result.append(part)
        else:
            result.append(part.translate(trans_table))
    
    return "".join(result)
