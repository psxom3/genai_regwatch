# test_email.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Load .env so it picks up your updated App Password
load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", SMTP_USER)

def send_test_email():
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "✅ Test Email from RegWatch"
        msg["From"] = ALERT_EMAIL_FROM
        msg["To"] = ALERT_EMAIL_TO

        html_content = """
        <h3>SMTP Test Successful 🎉</h3>
        <p>If you received this email, Gmail App Password authentication is working.</p>
        """
        msg.attach(MIMEText(html_content, "html"))

        # Connect to Gmail SMTP
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(ALERT_EMAIL_FROM, ALERT_EMAIL_TO.split(","), msg.as_string())
        server.quit()
        print("✅ Test email sent successfully to:", ALERT_EMAIL_TO)
    except Exception as e:
        print("❌ Failed to send test email:", e)

if __name__ == "__main__":
    send_test_email()
