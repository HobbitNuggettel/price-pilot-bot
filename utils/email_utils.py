import os
import smtplib
import logging
from email.mime.text import MIMEText
from config import SMTP_EMAIL, SMTP_PASSWORD, SMTP_SERVER, SMTP_PORT
from datetime import datetime
from utils.time_utils import format_time_ago

def send_email_alert(message, user_id):
    user_email = os.getenv(f"EMAIL_{user_id}")
    if not user_email:
        return

    from_email = SMTP_EMAIL
    password = SMTP_PASSWORD

    try:
        msg = MIMEText(message)
        msg['Subject'] = "Crypto Alert Triggered"
        msg['From'] = from_email
        msg['To'] = user_email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(from_email, password)
            server.sendmail(from_email, [user_email], msg.as_string())
    except Exception as e:
        logging.error(f"Email failed: {e}")

