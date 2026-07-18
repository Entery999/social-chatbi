from app.utils.logger import Logger
from app.ai.model.model import MyModel
from app.ai.tool.mysql_tool import mysql_tool
from app.ai.tool.send_email_tool import send_email
from app.ai.schema.emailResponse import EmailResponse
from langchain.agents import create_agent


logger = Logger().get_Logger(__name__)


class SystemAgent:
    def __init__(self):
        logger.info("初始化系统智能体")
        self.model = MyModel().get_model()
        self.tools = [mysql_tool, send_email]
        self.agent = self.__init__agent()

    def __init__agent(self):
        prompt = """
你是登录验证助手。用户给了你一个邮箱，请完成以下两步：

步骤一：用户消息中有具体的SQL语句，你直接把它传给mysql_tool执行

步骤二：如果存在，用 send_email 向该邮箱发送验证码邮件
  - 验证码必须是随机生成的4位数字
  - subject = "验证码"
  - content = "您的验证码是：XXXX"

反馈：
  查询为空 → 状态码500，验证码0，提示信息：邮箱未注册
  发送成功 → 状态码200，提示信息：发送成功
  发送失败 → 状态码500，提示信息：发送失败原因说明
        """
        agent = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=prompt,
            response_format=EmailResponse,
            debug=True
        )
        return agent

    def answer(self, email):
        import random
        code = str(random.randint(1000, 9999))
        result = send_email(email, "验证码", f"您的验证码是：{code}")
        if "成功" in result:
            return {"data": code, "subject": "验证码", "code": "200", "msg": "发送成功"}
        else:
            logger.error(f"邮件发送失败：{result}")
            return {"data": "0", "subject": "0", "code": "500", "msg": "发送失败"}







