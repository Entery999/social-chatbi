import smtplib
from email.mime.text import MIMEText
from email.header import Header
import os

from dotenv import load_dotenv
from app.utils.logger import Logger

load_dotenv()
logger = Logger().get_Logger(__name__)

def send_email(to:str, subject:str, content:str) -> str:
    """
    通过腾讯邮箱SMTP发送邮件（SMTP_SSL 端口465）
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
        logger.info(f"[邮件] 发送成功: {to}")
        return "邮件发送成功"
    except Exception as e:
        logger.error(f"[邮件] 发送失败: {e}")
        return f"邮件发送失败：{e}"



