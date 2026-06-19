import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "app.db")
REMINDER_POLL_SECONDS = int(os.getenv("REMINDER_POLL_SECONDS", "30"))
ADMIN_IDS = os.getenv("ADMIN_IDS", "1109928700")
