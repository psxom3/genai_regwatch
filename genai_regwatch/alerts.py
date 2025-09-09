import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from .config import SENDGRID_API_KEY, ALERT_EMAIL_TO, ALERT_EMAIL_FROM

def send_email_alert(title, summary, actions_json):
    """Send regulatory update alert via SendGrid"""
    message = Mail(
        from_email=ALERT_EMAIL_FROM,
        to_emails=ALERT_EMAIL_TO,
        subject=f"New RBI Regulatory Update: {title}",
        html_content=f"""
        <h3>{title}</h3>
        <p><b>Summary:</b></p>
        <p>{summary}</p>
        <p><b>Actions:</b></p>
        <pre>{actions_json}</pre>
        """
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"[ALERT] Email sent: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Failed to send alert: {e}")
