from database import connect_to_mongodb, get_collection, COLLECTIONS
connect_to_mongodb()
col = get_collection(COLLECTIONS["settings"])
chats = list(col.find({}))
print("Total groups:", len(chats))
for c in chats:
    cid = c.get("chat_id")
    title = c.get("title", "?")
    print("  chat_id=%s, title=%s" % (cid, title))
