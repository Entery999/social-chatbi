import json
import urllib.request
import urllib.error
import os

from dotenv import load_dotenv
from app.utils.logger import Logger

load_dotenv()
logger = Logger().get_Logger(__name__)

def send_email(to:str, subject:str, content:str) -> str:
    """
    通过 Resend HTTP API 发送邮件（HTTPS 443，兼容 Render 免费实例）
    """
    api_key = os.getenv("RESEND_API_KEY", "")
    sender = "onboarding@resend.dev"
    logger.info(f"[邮件] 准备发送: to={to}, from={sender}")
    try:
        payload = json.dumps({
            "from": sender,
            "to": [to],
            "subject": subject,
            "text": content
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        logger.info(f"[邮件] 正在调用 Resend API...")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            logger.info(f"[邮件] 发送成功: {to}, id={body.get('id')}")
            return "邮件发送成功"
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        logger.error(f"[邮件] Resend API 错误: {e.code} {err_body}")
        return f"邮件发送失败：API错误 {e.code} {err_body}"
    except Exception as e:
        logger.error(f"[邮件] 发送异常: {type(e).__name__}: {e}")
        return f"邮件发送失败：{type(e).__name__}: {e}"



