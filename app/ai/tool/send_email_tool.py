import smtplib
import socket
from email.mime.text import MIMEText
from email.header import Header
import os

from dotenv import load_dotenv
from app.utils.logger import Logger

load_dotenv()
logger = Logger().get_Logger(__name__)

def send_email(to:str, subject:str, content:str) -> str:
    """
    发送邮件
    """
    host = os.getenv("EMAIL_HOST", "smtp.qq.com")
    user = os.getenv("EMAIL_FROM")
    pwd = os.getenv("EMAIL_PASSWORD")
    logger.info(f"[邮件] 准备发送: to={to}, host={host}, user={user}")
    try:
        msg = MIMEText(content, 'plain', 'utf-8')
        msg['To'] = to
        msg['From'] = user
        msg['Subject'] = Header(subject, 'utf-8')

        logger.info(f"[邮件] 正在连接SMTP: {host}:465 (SSL)...")
        smtp = smtplib.SMTP_SSL(host, 465, timeout=15)
        logger.info(f"[邮件] SMTP连接成功，正在登录...")
        smtp.login(user, pwd)
        logger.info(f"[邮件] 登录成功，正在发送...")
        smtp.sendmail(user, to, msg.as_string())
        smtp.quit()
        logger.info(f"[邮件] 发送成功: {to}")
        return "邮件发送成功"
    except socket.timeout as e:
        logger.error(f"[邮件] SMTP连接超时: {e}")
        return f"邮件发送失败：SMTP连接超时 {e}"
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"[邮件] SMTP认证失败: {e}")
        return f"邮件发送失败：SMTP认证失败 {e}"
    except Exception as e:
        logger.error(f"[邮件] 发送异常: {type(e).__name__}: {e}")
        return f"邮件发送失败：{type(e).__name__}: {e}"



