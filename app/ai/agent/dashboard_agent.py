from app.utils.logger import Logger
from app.ai.model.model import MyModel
from app.ai.tool.mysql_tool import mysql_tool
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from datetime import datetime
import os, json, re
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
logger = Logger().get_Logger(__name__)

DASHBOARD_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.0/echarts.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Microsoft YaHei', sans-serif; background: #f0f2f5; padding: 20px; }}
        h1 {{ text-align: center; color: #1a1a2e; margin-bottom: 20px; font-size: 24px; }}
        .dashboard {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 20px; max-width: 1400px; margin: 0 auto; }}
        .chart-card {{ background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .chart-box {{ width: 100%; height: 400px; }}
        .footer {{ text-align: center; color: #999; margin-top: 30px; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="dashboard">
{charts_html}
    </div>
    <div class="footer">便民 ChatBI 仪表盘 · 生成于 {timestamp}</div>
    <script>
{scripts}
    </script>
</body>
</html>"""


class DashboardAgent:
    def __init__(self):
        logger.info("初始化仪表盘智能体")
        self.model = ChatOpenAI(
            model=os.getenv("MODEL_NAME"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_BASE"),
            max_tokens=2048,
            temperature=0.3
        )
        self.tools = [mysql_tool]
        self.agent = self.__init_agent()

    def __init_agent(self):
        prompt = """你是一个政务社保仪表盘生成助手，你有一个工具：mysql_tool。
先查询数据库获取真实数据，严禁捏造数据。

数据库表结构：
- population(id, age_0_14, age_15_64, age_65_plus, life_expectancy, birth_rate, death_rate)
- social_security(id, population_id, fund_balance, contribution_rate, benefit_rate)
- policy_record(id, population_id, policy_flag, adjustment_action)
- 关联：population.id = social_security.population_id = policy_record.population_id

你的任务：根据用户需求，生成包含多个图表的仪表盘。
请输出一个 JSON 数组，每个元素是一个 echarts option 对象，并包含 title 字段。
示例输出格式（必须严格遵守）：
[
  {"title":{"text":"人口年龄结构"},"tooltip":{},"xAxis":{"type":"category","data":["区域1","区域2"]},"yAxis":{"type":"value"},"series":[{"name":"少儿","type":"bar","data":[100,200]}]},
  {"title":{"text":"基金余额趋势"},"tooltip":{},"xAxis":{"type":"category","data":["1","2"]},"yAxis":{"type":"value"},"series":[{"name":"余额","type":"line","data":[900000,950000]}]}
]

要求：
1. 至少生成 2 个图表，最多 4 个
2. 图表类型要多样化（柱状图、折线图、饼图等搭配使用）
3. 只输出 JSON 数组，不要输出 markdown 代码块或多余文字"""
        logger.info("[仪表盘] 智能体创建完成")
        return create_react_agent(
            model=self.model,
            tools=self.tools,
            prompt=prompt,
        )

    def _extract_json_array(self, text: str) -> list:
        """从LLM输出中提取JSON数组"""
        # 尝试直接解析
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        # 查找文本中的 JSON 数组
        decoder = json.JSONDecoder()
        idx = 0
        while True:
            s = text.find("[", idx)
            if s == -1:
                break
            try:
                obj, end_pos = decoder.raw_decode(text, s)
                if isinstance(obj, list) and len(obj) >= 2:
                    return obj
                idx = end_pos
            except json.JSONDecodeError:
                idx = s + 1
        return []

    def _build_html(self, charts: list, title: str) -> str:
        """将多个 echarts option 组合成 HTML 页面"""
        charts_html_parts = []
        scripts = []
        for i, option in enumerate(charts):
            chart_id = f"chart_{i}"
            chart_title = option.get("title", {}).get("text", f"图表{i+1}")
            charts_html_parts.append(
                f'        <div class="chart-card"><div id="{chart_id}" class="chart-box"></div></div>'
            )
            scripts.append(
                f'    var {chart_id} = echarts.init(document.getElementById("{chart_id}"));\n'
                f'    {chart_id}.setOption({json.dumps(option, ensure_ascii=False)});'
            )

        return DASHBOARD_HTML_TEMPLATE.format(
            title=title,
            charts_html="\n".join(charts_html_parts),
            scripts="\n".join(scripts),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

    async def answer(self, question: str, user_id: str) -> dict:
        logger.info(f"[仪表盘] answer 开始, question={question[:50]}")
        try:
            result = await self.agent.ainvoke(
                {"messages": [{"role": "user", "content": question}]},
            )
            last_msg = result["messages"][-1]
            full = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
            logger.info(f"[仪表盘] LLM 完成，总长度{len(full)}")

            charts = self._extract_json_array(full)
            if not charts:
                logger.warning("[仪表盘] 未提取到图表数组")
                return {"code": 500, "msg": "未能生成有效的图表配置"}

            # 生成标题
            title = "社保数据分析仪表盘"
            for chart in charts:
                if isinstance(chart, dict) and "title" in chart:
                    break

            html = self._build_html(charts, title)

            # 保存 HTML 文件
            download_dir = Path(__file__).resolve().parent.parent.parent / "static" / "download"
            download_dir.mkdir(parents=True, exist_ok=True)
            filename = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            filepath = download_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html)

            base_url = os.getenv("RENDER_URL", "http://localhost:8000")
            download_url = f"{base_url}/static/download/{filename}"
            logger.info(f"[仪表盘] 生成成功: {download_url}, 含{len(charts)}个图表")
            return {"code": 200, "data": {"url": download_url, "chart_count": len(charts), "title": title}}

        except Exception as e:
            logger.error(f"[仪表盘] 异常: {e}", exc_info=True)
            return {"code": 500, "msg": str(e)}
