import smtplib
from email.mime.text import MIMEText
from email.header import Header
import os

from dotenv import load_dotenv

load_dotenv()

def send_email(to:str, subject:str, content:str) -> str:
    """
    发送邮件
    """
    try:
        msg = MIMEText(content, 'plain', 'utf-8')
        msg['To'] = to
        msg['From'] = os.getenv("EMAIL_FROM")
        msg['Subject'] = Header(subject, 'utf-8')

        smtp = smtplib.SMTP_SSL(os.getenv("EMAIL_HOST"), 465)
        smtp.login(os.getenv("EMAIL_FROM"), os.getenv("EMAIL_PASSWORD"))
        smtp.sendmail(os.getenv("EMAIL_FROM"), to, msg.as_string())
        smtp.quit()
        return "邮件发送成功"
    except Exception as e:
        print(e)
        return f"邮件发送失败：{e}"



