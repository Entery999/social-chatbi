from app.utils.logger import Logger
from app.ai.model.model import MyModel
from app.ai.tool.mysql_tool import mysql_tool
# from app.utils.permission_middle import check_permission  # langgraph版本不支持middleware参数
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

logger = Logger().get_Logger(__name__)
class SQLQuestionAgent:
    def __init__(self):
        logger.info("初始化sql问答智能体")
        self.model = MyModel().get_model()
        self.tools = self.__init__tools()
        self.agent = self.__init__agent()

    def __init__tools(self):
        self.tools = [mysql_tool]
        return self.tools

    def __init__agent(self):
        prompt = """
一、你是一个政务便民数据问答助手，你有一个工具：mysql_tool。根据用户的自然语言问题生成SQL查询并执行，用中文回答。

二、重要规则：
1. 只能进行SELECT查询操作，严禁使用INSERT、UPDATE、DELETE、DROP、ALTER等写操作
2. 数据库包含以下3张关联表：
   - population(id, age_0_14, age_15_64, age_65_plus, life_expectancy, birth_rate, death_rate) — 人口统计表，记录各区域的人口年龄分层与健康指标
   - social_security(id, population_id, fund_balance, contribution_rate, benefit_rate) — 社保基金表，通过population_id关联人口记录
   - policy_record(id, population_id, policy_flag, adjustment_action) — 政策记录表，通过population_id关联人口记录
   - user_info(id, user_name, email, role) — 系统用户表，与社保业务无关
3. 表关联关系：population.id = social_security.population_id = policy_record.population_id
4. 字段含义：
   - age_0_14: 0-14岁少儿人口数
   - age_15_64: 15-64岁劳动人口数
   - age_65_plus: 65岁以上老年人口数
   - life_expectancy: 预期寿命(岁)
   - birth_rate: 出生率(‰)
   - death_rate: 死亡率(‰)
   - fund_balance: 社保基金余额(元)
   - contribution_rate: 缴费率(%)
   - benefit_rate: 待遇发放率(%)
   - policy_flag: 是否触发政策调整(0=否, 1=是)
   - adjustment_action: 调整措施类型(0=维持不变, 1=微调, 2=大调)
5. 常见查询示例：
   - 查询老龄化最严重的区域：SELECT * FROM population ORDER BY age_65_plus DESC LIMIT 10
   - 查询社保基金余额与缴费率的关系：SELECT p.id, s.fund_balance, s.contribution_rate FROM population p JOIN social_security s ON p.id = s.population_id
   - 统计触发政策调整的记录数：SELECT COUNT(*) FROM policy_record WHERE policy_flag = 1
6. 列名和表名不区分大小写
        """
        logger.info("[SQL问答] create_react_agent 创建完成")
        agent = create_react_agent(
            model=self.model,
            tools=self.tools,
            prompt=prompt,
            checkpointer=InMemorySaver(),
            # middleware=[check_permission],  # langgraph版本不支持，改为在chat_router中前置校验
        )
        return agent

    async def create_question(self, question: str, user_id: str):
        logger.info(f"[SQL问答] 开始流式请求 LLM, question={question[:50]}")
        token_count = 0
        try:
            responses = self.agent.astream(
                {"messages": [{"role": "user", "content": question, "additional": {"user_id": user_id}}]},
                {"configurable": {"thread_id": user_id, "user_id": user_id}},
                stream_mode="messages"
            )
            async for c, m in responses:
                if not getattr(c, "content", None):
                    continue
                if isinstance(m, dict) and m.get("langgraph_node") == "tools":
                    logger.info(f"[SQL问答] 跳过工具节点消息: {str(c.content)[:100]}")
                    continue
                token_count += 1
                yield c.content
        except Exception as e:
            logger.error(f"[SQL问答] 流式请求异常: {e}", exc_info=True)
            yield f"请求出错: {str(e)}"
        logger.info(f"[SQL问答] 流式完成，共{token_count}个token")

    async def answer(self, question: str, user_id: str):
        async for text in self.create_question(question, user_id):
            yield text
