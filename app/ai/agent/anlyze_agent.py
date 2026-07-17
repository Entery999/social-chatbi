from app.utils.logger import Logger
from app.ai.model.model import MyModel
from app.ai.tool.mysql_tool import mysql_tool
from app.ai.schema.anlyze_response import AnalyzeResponse
from langchain.agents import create_agent

logger = Logger().get_Logger(__name__)

class AnalyzeAgent:
    def __init__(self):
        logger.info("初始化数据分析智能体")
        self.model = MyModel().get_model()
        self.tools = self.__init_tools()
        self.agent = self.__init_agent()

    def __init_tools(self):
        self.tools = [mysql_tool]
        return self.tools

    def __init_agent(self):
        prompt = """
你是一个政务社保数据分析助手，你有一个工具：mysql_tool

数据库表结构：
- population(id, age_0_14, age_15_64, age_65_plus, life_expectancy, birth_rate, death_rate) — 人口统计
- social_security(id, population_id, fund_balance, contribution_rate, benefit_rate) — 社保基金
- policy_record(id, population_id, policy_flag, adjustment_action) — 政策记录
- 关联：population.id = social_security.population_id = policy_record.population_id

工作流程：
步骤一：查询数据，把数据以表格形式存入表格数据（column_name 是中文表头数组，data 是对象数组）
步骤二：根据问题做出数据分析（如老龄化趋势、基金收支平衡、缴费率与待遇率对比等），存入 result
步骤三：生成一个 echarts 图表 JSON 配置，存入 json（必须是合法的 echarts option 字符串）

SQL规范：只能 SELECT，涉及排名用 ORDER BY + LIMIT，多表查询用 JOIN
"""
        logger.info("[分析] create_agent 创建完成")
        return create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=prompt,
            response_format=AnalyzeResponse,
        )

    def answer(self, question: str, user_id: str) -> dict:
        logger.info(f"[分析] answer 开始, question={question[:50]}")
        try:
            logger.info("[分析] 调用 agent.invoke ...")
            response = self.agent.invoke(
                {"messages": [{"role": "user", "content": question}]},
            )
            logger.info("[分析] agent.invoke 返回成功")
            if "structured_response" not in response:
                logger.error(f"[分析] 响应中缺少 structured_response, keys={list(response.keys())}")
                return {"code": 500, "msg": "模型响应格式异常"}
            data = response["structured_response"].model_dump()
            logger.info(f"[分析] 结构化数据: table列数={len(data.get('table',{}).get('column_names',[]))}, result长度={len(data.get('result',''))}, 有json={bool(data.get('json',''))}")
            return {"code": 200, "data": data}
        except KeyError as e:
            logger.error(f"[分析] 响应key缺失: {e}", exc_info=True)
            return {"code": 500, "msg": f"数据解析失败: {e}"}
        except Exception as e:
            logger.error(f"[分析] 异常: {e}", exc_info=True)
            return {"code": 500, "msg": str(e)}
