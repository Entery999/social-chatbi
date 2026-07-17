import smtplib
import os
from email.mime.text import MIMEText
from email.header import Header

from dotenv import load_dotenv
from app.utils.logger import Logger

load_dotenv()
logger = Logger().get_Logger(__name__)

def send_email(to:str, subject:str, content:str) -> str:
    """
    通过 Gmail SMTP 发送邮件
    """
    host = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    port = int(os.getenv("EMAIL_PORT", "587"))
    user = os.getenv("EMAIL_USER")
    pwd = os.getenv("EMAIL_PASSWORD")
    sender = os.getenv("EMAIL_FROM", user)
    logger.info(f"[邮件] 准备发送: to={to}, from={sender}, host={host}:{port}")
    try:
        msg = MIMEText(content, 'plain', 'utf-8')
        msg['To'] = to
        msg['From'] = sender
        msg['Subject'] = Header(subject, 'utf-8')

        logger.info(f"[邮件] 正在连接 SMTP: {host}:{port} (STARTTLS)...")
        smtp = smtplib.SMTP(host, port, timeout=15)
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        logger.info(f"[邮件] TLS 连接成功，正在登录...")
        smtp.login(user, pwd)
        logger.info(f"[邮件] 登录成功，正在发送...")
        smtp.sendmail(sender, to, msg.as_string())
        smtp.quit()
        logger.info(f"[邮件] 发送成功: {to}")
        return "邮件发送成功"
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"[邮件] SMTP 认证失败: {e}")
        return f"邮件发送失败：SMTP 认证失败 {e}"
    except Exception as e:
        logger.error(f"[邮件] 发送异常: {type(e).__name__}: {e}")
        return f"邮件发送失败：{type(e).__name__}: {e}"



