import os
from dotenv import load_dotenv
import pathlib

load_dotenv()

# RBI URL
RBI_NOTIFICATIONS_URL = "https://rbi.org.in/Scripts/NotificationUser.aspx"

# NHB URL
NHB_NOTIFICATIONS_URL = "https://www.nhb.org.in/whats-new-2/"


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

# OLLAMA 
# Example: http://localhost:11434
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
# model name you have in Ollama (e.g., "llama2", "mistral", "your-ollama-model")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


# SMTP Email (UPDATED: using direct SMTP instead of SendGrid)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "mainkaromkar13@gmail.com")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", SMTP_USER or "mainkaromkar13@gmail.com")

# Parallel workers
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 3))
