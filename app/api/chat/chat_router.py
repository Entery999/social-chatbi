import json
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pydantic import BaseModel
from app.utils.logger import Logger
from app.utils.permission_role import permission_role
import os
import pymysql
from dotenv import load_dotenv

load_dotenv()
logger = Logger().get_Logger(__name__)
chat_router = APIRouter()


def _check_permission(user_id: str):
    """统一权限前置校验：只有允许的角色才能使用系统"""
    role = permission_role(user_id)
    allowed_roles = ["总经理"]
    if role is None or role == "None":
        return "用户不存在"
    if role == "查询失败":
        return "查询用户角色失败"
    if role not in allowed_roles:
        return f"权限不足，当前角色：{role}"
    logger.info(f"[权限] 用户 {user_id} 角色 {role} 校验通过")
    return None

class ChatBody(BaseModel):
    question: str
    user_id: str

class FeedbackBody(BaseModel):
    question: str
    answer: str = ""
    feedback_text: str = ""
    user_id: str = ""

@chat_router.get("/chat")
async def chat_get(request: Request, question: str, user_id: str):
    logger.info(f"[路由] GET /chat  question={question[:50]}  user_id={user_id}")

    # 统一权限前置校验
    perm_error = _check_permission(user_id)
    if perm_error:
        logger.warning(f"[权限] 拒绝访问: {perm_error}")
        return JSONResponse(status_code=403, content={"code": 403, "msg": perm_error})

    if "仪表盘" in question:
        logger.info("[路由] → 仪表盘智能体")
        agent = request.app.state.dashboard_agent
        result = await agent.answer(question, user_id)
        logger.info(f"[路由] 仪表盘返回: {str(result)[:200]}")
        return result

    if "图表" in question:
        logger.info("[路由] → 图表智能体")
        agent = request.app.state.echarts_agent
        result = await agent.answer(question, user_id)
        logger.info(f"[路由] 图表返回: {str(result)[:200]}")
        return result

    if "数据分析" in question:
        logger.info("[路由] → 数据分析智能体")
        agent = request.app.state.analyze_agent
        result = agent.answer(question, user_id)
        logger.info(f"[路由] 数据分析返回: {str(result)[:200]}")
        return result

    if "上传文件成功:" in question:
        logger.info("[路由] → 文件分析智能体 (SSE流式)")
        async def file_gen():
            try:
                agent = request.app.state.file_analyze_agent
                async for chunk in agent.answer(question, user_id):
                    yield f"data:{json.dumps({'content': chunk, 'done': False}, ensure_ascii=False)}\n\n"
                yield f"data:{json.dumps({'content': '', 'done': True}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"[路由] 文件分析错误: {e}", exc_info=True)
                yield f"data:{json.dumps({'content': '服务出错', 'done': True}, ensure_ascii=False)}\n\n"
        return StreamingResponse(content=file_gen(), media_type="text/event-stream")

    logger.info("[路由] → SQL问答智能体 (SSE流式)")
    # 设置查询上下文（供 mysql_tool 记录日志）
    from app.ai.tool.mysql_tool import set_query_context
    set_query_context(question, user_id)

    async def generator():
        try:
            agent = request.app.state.sql_question_agent
            chunk_count = 0
            async for chunk in agent.answer(question, user_id):
                chunk_count += 1
                yield f"data:{json.dumps({'content': chunk, 'done': False}, ensure_ascii=False)}\n\n"
            logger.info(f"[路由] SQL问答完成，共{chunk_count}个chunk")
            yield f"data:{json.dumps({'content': '', 'done': True}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"[路由] 流式返回错误：{str(e)}", exc_info=True)
            yield f"data:{json.dumps({'content': '服务出错', 'done': True}, ensure_ascii=False)}\n\n"

    return StreamingResponse(content=generator(), media_type="text/event-stream")

@chat_router.post("/chat")
async def chat_post(request: Request, body: ChatBody):
    logger.info(f"[路由] POST /chat  question={body.question[:50]}  user_id={body.user_id}")
    return await chat_get(request, body.question, body.user_id)

@chat_router.post("/feedback")
async def submit_feedback(body: FeedbackBody):
    """错误反馈接口：用户提交错误结果反馈"""
    logger.info(f"[反馈] user={body.user_id}, question={body.question[:50]}")
    try:
        conn = pymysql.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            db=os.getenv("MYSQL_DB"),
            port=int(os.getenv("MYSQL_PORT")),
            charset='utf8',
        )
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedback (question, answer, feedback_text, user_id) VALUES (%s, %s, %s, %s)",
            (body.question, body.answer[:2000], body.feedback_text[:2000], body.user_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("[反馈] 写入成功")
        return {"code": 200, "msg": "反馈提交成功，感谢您的反馈"}
    except Exception as e:
        logger.error(f"[反馈] 写入失败: {e}", exc_info=True)
        return {"code": 500, "msg": f"反馈提交失败: {e}"}

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent.parent

@chat_router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    upload_dir = os.path.join(BASE_DIR, "static/upload")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    logger.info(f"上传文件：{file_path}")
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return {"code": 200, "filename": file.filename}

@chat_router.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(BASE_DIR, "static/download", filename)
    if not os.path.exists(file_path):
        return {"code": 404, "msg": "文件不存在"}
    return FileResponse(path=file_path, filename=filename)
