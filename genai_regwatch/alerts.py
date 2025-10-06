import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from .config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, ALERT_EMAIL_TO, ALERT_EMAIL_FROM

def send_email_alert(regulator, title, url, summary, actions_json):
    """
    Send email using SMTP with regulator, proper title and URL.
    """
    try:
        msg = MIMEMultipart("alternative")
        # Add regulator prefix in subject
        msg["Subject"] = f"[{regulator}] New Regulatory Update: {title}"
        msg["From"] = ALERT_EMAIL_FROM
        msg["To"] = ALERT_EMAIL_TO

        html_content = f"""
        <h3>{title}</h3>
        <p><b>Regulator:</b> {regulator}</p>
        <p><a href="{url}" target="_blank">📄 View Original Document</a></p>
        <p><b>Summary:</b></p>
        <p>{summary}</p>
        <p><b>Actions:</b></p>
        <pre>{actions_json}</pre>
        """

        part = MIMEText(html_content, "html")
        msg.attach(part)

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.ehlo()
        server.starttls()
        if SMTP_USER and SMTP_PASS:
            server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(ALERT_EMAIL_FROM, ALERT_EMAIL_TO.split(","), msg.as_string())
        server.quit()
        print("[ALERT] Email sent via SMTP.")
    except Exception as e:
        print(f"[ERROR] Failed to send email via SMTP: {e}")
