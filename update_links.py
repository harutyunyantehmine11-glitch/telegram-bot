import sqlite3

BOT_USERNAME = "Your108Referall_bot"  # ← твой реальный username

conn = sqlite3.connect("referrals.db")
cur = conn.cursor()

cur.execute("SELECT user_id FROM users")
rows = cur.fetchall()

for (uid,) in rows:
    new_link = f"https://t.me/{BOT_USERNAME}?start={uid}"
    cur.execute("UPDATE users SET referral_link=? WHERE user_id=?", (new_link, uid))

conn.commit()
conn.close()
print("Links updated.")
