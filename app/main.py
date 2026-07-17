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
import pymysql
import ssl

loggger = Logger().get_Logger(__name__)

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend_dist"

def init_cloud_database():
    """启动时自动初始化云数据库：创建表并导入数据（仅在表不存在时执行）"""
    try:
        mysql_host = os.getenv("MYSQL_HOST", "")
        conn_kwargs = dict(
            host=mysql_host,
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            db=os.getenv("MYSQL_DB"),
            port=int(os.getenv("MYSQL_PORT", 3306)),
            connect_timeout=15,
        )
        if "aivencloud" in mysql_host:
            conn_kwargs["ssl"] = {"ssl": ssl.create_default_context()}
        conn = pymysql.connect(**conn_kwargs)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        if len(tables) >= 5:
            loggger.info(f"[数据库] 已有 {len(tables)} 张表，跳过初始化")
            cursor.close()
            conn.close()
            return
        loggger.info("[数据库] 表不存在或不足，开始导入 init_db.sql ...")
        sql_file = ROOT_DIR / "init_db.sql"
        if not sql_file.exists():
            loggger.warning("[数据库] init_db.sql 不存在，跳过导入")
            cursor.close()
            conn.close()
            return
        sql_content = sql_file.read_text(encoding="utf-8")
        # 按分号分割语句，逐条执行
        for statement in sql_content.split(";"):
            statement = statement.strip()
            if statement and not statement.startswith("--") and not statement.startswith("/*!"):
                try:
                    cursor.execute(statement)
                except Exception as e:
                    loggger.warning(f"[数据库] 语句执行警告: {e}")
        conn.commit()
        cursor.close()
        conn.close()
        loggger.info("[数据库] init_db.sql 导入完成")
    except Exception as e:
        loggger.error(f"[数据库] 初始化失败: {e}", exc_info=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_cloud_database()
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
