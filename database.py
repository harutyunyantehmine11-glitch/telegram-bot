import sqlite3

# Создание базы данных
conn = sqlite3.connect("referrals.db")
cursor = conn.cursor()

# Таблица для пользователей
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    referral_link TEXT
)
""")

conn.commit()
conn.close()

