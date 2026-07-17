from pathlib import Path
from app.ai.tool.docx_read_tool import docx_read_tool
from app.ai.tool.docx_write_tool import docx_write_tool
from app.utils.logger import Logger
from app.ai.model.model import MyModel
from langchain.agents import create_agent
import os
from langchain_core.prompts import PromptTemplate

logger = Logger().get_Logger(__name__)

class FileAnalyzeAgent:
    def __init__(self):
        logger.info("初始化文件分析智能体")
        self.model = MyModel().get_model()
        self.tools = self.__init_tools()

    def __init_tools(self):
        self.tools = [docx_read_tool, docx_write_tool]
        return self.tools

    async def answer(self, question: str, user_id: str):
        prompt = """
            你是一个文件分析助手，你有两个工具
            docx_read_tool
            docx_write_tool
            工作流程：
            步骤一：调用docx_read_tool工具读取文档，文件路径是：{path}
            步骤二：分析文档内容，查看数据是否有缺失和重复的数据，如果有缺失值就填充None，删除重复数据
            步骤三：调用docx_write_tool把分析过后的数据写入文档
            把分析的数据结果和下载地址返回给用户
        """
        base_dir = Path(__file__).resolve().parent.parent.parent
        upload_dir = base_dir / "static/upload"
        path = os.path.join(upload_dir, question.split(":")[1])
        logger.info(f"文件路径: {path}")
        prompt_temple = PromptTemplate.from_template(prompt)
        prompt = prompt_temple.format(path=path)

        agent = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=prompt,
            debug=False,
        )
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]},
        )
        msgs = result.get("messages", [])
        output = msgs[-1].content if msgs and hasattr(msgs[-1], "content") and msgs[-1].content else str(msgs)
        yield output
