from fastapi import FastAPI
from fastapi.responses import FileResponse
import os
from app.ai.agent.sql_question_agent import SQLQuestionAgent
from app.ai.agent.system_agent import SystemAgent
from app.utils.logger import Logger
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from app.ai.agent.anlyze_agent import AnalyzeAgent
from app.ai.agent.echarts_agent import EchartsAgent
from app.ai.agent.file_analyze_agent import FileAnalyzeAgent
from app.ai.agent.dashboard_agent import DashboardAgent
from starlette.staticfiles import StaticFiles
from app.api.chat.chat_router import chat_router
from app.api.system.system_router import system_router
from contextlib import asynccontextmanager
from pathlib import Path

loggger = Logger().get_Logger(__name__)

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend_dist"

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.system_agent = SystemAgent()
    app.state.sql_question_agent = SQLQuestionAgent()
    app.state.analyze_agent = AnalyzeAgent()
    app.state.echarts_agent = EchartsAgent()
    app.state.file_analyze_agent = FileAnalyzeAgent()
    app.state.dashboard_agent = DashboardAgent()
    loggger.info("全部智能体创建完成")
    yield
    loggger.info("销毁系统智能体")

app = FastAPI(lifespan=lifespan)
app.include_router(system_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.include_router(chat_router)

# 前端静态资源（Vue3 dist）
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="frontend_assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # 尝试返回前端静态文件
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        # 其他路径返回 index.html（SPA 路由）
        return FileResponse(str(FRONTEND_DIR / "index.html"))

if __name__ == "__main__":
    uvicorn.run(app,
                host="0.0.0.0",
                port=int(os.getenv("PORT", 8000)),
                )
