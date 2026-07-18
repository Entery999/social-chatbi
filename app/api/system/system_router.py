from fastapi import APIRouter,Request
from app.api.schema.login_schema import LoginSchema,SendCodeSchema,RegisterSchema,RegisterSendCodeSchema
from app.ai.agent.system_agent import SystemAgent
from app.utils.logger import Logger
import redis
import os
import pymysql
import ssl
from dotenv import load_dotenv
load_dotenv()

_ssl_ctx = ssl.create_default_context()

def _mysql_kwargs(**extra):
    """构造MySQL连接参数，云数据库自动启用SSL"""
    kwargs = dict(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        db=os.getenv("MYSQL_DB"),
        port=int(os.getenv("MYSQL_PORT")),
    )
    if "aivencloud" in (os.getenv("MYSQL_HOST") or ""):
        kwargs["ssl"] = {"ssl": _ssl_ctx}
    kwargs.update(extra)
    return kwargs

#实例化redis连接（支持Upstash TLS）
_redis_ssl = os.getenv("REDIS_PASSWORD") is not None
redis_con = redis.Redis(
    host=os.getenv("REDIS_HOST", "127.0.0.1"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD", None),
    db=0,
    protocol=2,
    ssl=_redis_ssl,
)

system_router = APIRouter()

logger = Logger().get_Logger(__name__)

def _check_email_exists(email: str) -> bool:
    try:
        con = pymysql.connect(**_mysql_kwargs())
        cursor = con.cursor()
        cursor.execute("SELECT email FROM user_info WHERE email = %s", (email,))
        result = cursor.fetchall()
        cursor.close()
        con.close()
        return len(result) > 0
    except Exception as e:
        logger.error(f"数据库查询失败：{e}")
        return False

#注册邮箱发送验证码接口
@system_router.post("/send_code")
def send_code(args:SendCodeSchema,request:Request):
    logger.info(f"[登录]请求发送验证码，邮箱：{args.email}")
    if not _check_email_exists(args.email):
        return {"code": 500, "msg": "邮箱未注册"}
    agent: SystemAgent = request.app.state.system_agent
    rs = agent.answer(args.email)
    if rs["code"] == "200":
        redis_con.set(f"login:code:{args.email}", rs["data"], ex=60)
        print(f"\n===== 验证码：{rs['data']}，邮箱：{args.email} =====\n")
    logger.info(f"[登录]验证码发送结果：{rs}")
    return {"code": rs["code"], "msg": rs["msg"]}
#注册登录接口
@system_router.post("/login")
def login(args:LoginSchema):
    logger.info(f"[登录]请求登录，邮箱{args.email}")
    try:
        redis_key = f"login:code:{args.email}"
        code_bytes = redis_con.get(redis_key)
        if code_bytes and code_bytes.decode() == args.code:
            return{"code":200,"msg":"登录成功"}
        else:
            return{"code":500,"msg":"验证码错误或已过期"}
    except Exception as e:
        logger.error(f"[登录]登录异常：{e}",exc_info=True)
        return {"code":500,"msg":"登录失败"}

@system_router.post("/register_send_code")
def register_send_code(args:RegisterSendCodeSchema, request:Request):
    logger.info(f"[注册]请求发送验证码，邮箱：{args.email}")
    if _check_email_exists(args.email):
        return {"code": 500, "msg": "邮箱已注册"}
    agent: SystemAgent = request.app.state.system_agent
    rs = agent.answer(args.email)
    if rs["code"] == "200":
        redis_con.set(f"register:code:{args.email}", rs["data"], ex=60)
        print(f"\n===== 注册验证码：{rs['data']}，邮箱：{args.email} =====\n")
    logger.info(f"[注册]验证码发送结果：{rs}")
    return {"code": rs["code"], "msg": rs["msg"]}

@system_router.post("/register")
def register(args:RegisterSchema):
    logger.info(f"[注册]请求注册，邮箱：{args.email}")
    redis_key = f"register:code:{args.email}"
    code_bytes = redis_con.get(redis_key)
    if not code_bytes or code_bytes.decode() != args.code:
        return {"code": 500, "msg": "验证码错误或已过期"}
    try:
        con = pymysql.connect(**_mysql_kwargs())
        cursor = con.cursor()
        user_name = args.email.split("@")[0]
        cursor.execute(
            "INSERT INTO user_info (user_name, email, role) VALUES (%s, %s, %s)",
            (user_name, args.email, "员工")
        )
        con.commit()
        cursor.close()
        con.close()
        redis_con.delete(redis_key)
        logger.info(f"[注册]注册成功：{args.email}")
        return {"code": 200, "msg": "注册成功"}
    except Exception as e:
        logger.error(f"[注册]注册异常：{e}", exc_info=True)
        return {"code": 500, "msg": "注册失败"}
