from app.utils.logger import Logger
from app.ai.tool.mysql_tool import mysql_tool
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import os, json
from dotenv import load_dotenv

load_dotenv()
logger = Logger().get_Logger(__name__)

class EchartsAgent:
    def __init__(self):
        logger.info("初始化图表智能体")
        self.model = ChatOpenAI(
            model=os.getenv("MODEL_NAME"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_BASE"),
            max_tokens=256,
            temperature=0.3
        )
        self.tools = self.__init_tools()
        self.agent = self.__init_agent()

    def __init_tools(self):
        self.tools = [mysql_tool]
        return self.tools

    def __init_agent(self):
        prompt = """你是一个政务社保图表生成助手，你有一个工具：mysql_tool
先查询数据库获取真实数据，严禁捏造数据。

数据库表结构：
- population(id, age_0_14, age_15_64, age_65_plus, life_expectancy, birth_rate, death_rate)
- social_security(id, population_id, fund_balance, contribution_rate, benefit_rate)
- policy_record(id, population_id, policy_flag, adjustment_action)
- 关联：population.id = social_security.population_id = policy_record.population_id

根据用户要求生成 echarts 图表的 JSON 配置。常见图表示例：
- 人口年龄结构柱状图：xAxis为区域ID，series包含少儿/劳动/老年三组数据
- 社保基金余额折线图：xAxis为记录ID，yAxis为fund_balance
- 政策调整分布饼图：统计adjustment_action=0/1/2的占比
- 出生率与死亡率对比：双series折线图

输出格式示例：
{"title":{"text":"标题"},"tooltip":{},"xAxis":{"type":"category","data":["A","B"]},"yAxis":{"type":"value"},"series":[{"name":"系列","type":"bar","data":[10,20]}]}

雷达图用 radar 字段代替 xAxis/yAxis，热力图用 visualMap。
输出 echarts 标准 option JSON，不要 markdown 代码块，不要多余文字。"""
        logger.info("[图表] 智能体创建完成")
        return create_react_agent(
            model=self.model,
            tools=self.tools,
            prompt=prompt,
        )

    async def answer(self, question: str, user_id: str) -> dict:
        logger.info(f"[图表] answer 开始, question={question[:50]}")
        try:
            logger.info("[图表] 开始请求 LLM")
            result = await self.agent.ainvoke(
                {"messages": [{"role": "user", "content": question}]},
            )
            last_msg = result["messages"][-1]
            full = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
            logger.info(f"[图表] LLM 完成，总长度{len(full)}")

            logger.info(f"[图表] 解析JSON: 全文长度={len(full)}")
            chart_option = None
            decoder = json.JSONDecoder()
            candidates = []
            idx = 0
            while True:
                s = full.find("{", idx)
                if s == -1:
                    break
                try:
                    obj, end_pos = decoder.raw_decode(full, s)
                    candidates.append((end_pos - s, obj))
                    idx = end_pos
                except json.JSONDecodeError:
                    idx = s + 1

            logger.info(f"[图表] 共找到{len(candidates)}个JSON对象")

            for size, obj in sorted(candidates, key=lambda x: -x[0]):
                if isinstance(obj, dict) and ("series" in obj or "xAxis" in obj or "radar" in obj):
                    chart_option = obj
                    logger.info(f"[图表] 选择含series/radar的JSON(大小{size}): {str(chart_option)[:200]}")
                    break

            if chart_option is None and candidates:
                chart_option = max(candidates, key=lambda x: x[0])[1]
                logger.info(f"[图表] 无合格JSON，取最大JSON: {str(chart_option)[:200]}")

            if chart_option is None:
                logger.warning(f"[图表] 未找到任何JSON，使用全文前50字做标题")
                chart_option = {"title": {"text": full.strip()[:50]}, "xAxis": {"data": []}, "yAxis": {}, "series": []}

            return {"code": 200, "data": chart_option}
        except json.JSONDecodeError as e:
            logger.error(f"[图表] JSON解析失败: {e}, 原文: {full[-200:]}")
            return {"code": 500, "data": {}, "msg": f"图表JSON格式错误: {e}"}
        except Exception as e:
            logger.error(f"[图表] 异常: {e}", exc_info=True)
            return {"code": 500, "data": {}, "msg": str(e)}
