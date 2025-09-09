import os
from dotenv import load_dotenv

load_dotenv()

# RBI URL
RBI_NOTIFICATIONS_URL = "https://rbi.org.in/Scripts/NotificationUser.aspx"

# Local storage path
LOCAL_STORAGE = os.path.join(os.getcwd(), "storage", "raw")
#os.makedirs(LOCAL_STORAGE, exist_ok=True)
if not os.path.exists(LOCAL_STORAGE):
    os.makedirs(LOCAL_STORAGE)


# DB Config
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "regdb"),
    "user": os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASS", "password"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
}

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# SendGrid
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM")
