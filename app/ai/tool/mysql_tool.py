from langchain.tools import tool
from app.ai.schema.mysqlSchema import MysqlSchema
from app.utils.logger import Logger
import os
from dotenv import load_dotenv
import pymysql
from contextvars import ContextVar

load_dotenv()
logger = Logger().get_Logger(__name__)

# 上下文变量：存储当前用户问题，供日志记录使用
_current_question: ContextVar[str] = ContextVar("current_question", default="")
_current_user_id: ContextVar[str] = ContextVar("current_user_id", default="")


def set_query_context(question: str, user_id: str = ""):
    """设置当前查询上下文（在Agent调用前调用）"""
    _current_question.set(question)
    _current_user_id.set(user_id)


def _log_query(sql: str):
    """记录查询日志到 MySQL"""
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
            "INSERT INTO query_log (question, sql_text, user_id) VALUES (%s, %s, %s)",
            (_current_question.get(""), sql[:2000], _current_user_id.get(""))
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.warning(f"[MySQL] 查询日志写入失败: {e}")


@tool("mysql_tool", args_schema=MysqlSchema)
def mysql_tool(sql: str) -> str:
    """
    执行mysql查询
    数据库包含3张业务表：
    - population(id, age_0_14, age_15_64, age_65_plus, life_expectancy, birth_rate, death_rate) — 人口统计表
    - social_security(id, population_id, fund_balance, contribution_rate, benefit_rate) — 社保基金表
    - policy_record(id, population_id, policy_flag, adjustment_action) — 政策记录表
    关联关系：population.id = social_security.population_id = policy_record.population_id
    - user_info(id, user_name, email, role) — 系统用户表，与业务无关
    """
    try:
        logger.info(f"[MySQL] 执行SQL: {sql[:200]}")
        _log_query(sql)
        con = pymysql.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            db=os.getenv("MYSQL_DB"),
            port=int(os.getenv("MYSQL_PORT")),
            charset='utf8',
        )
        cursor = con.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        row_count = len(result)
        logger.info(f"[MySQL] 查询完成，共{row_count}条")
        if row_count > 0:
            logger.info(f"[MySQL] 首行数据: {str(result[0])[:200]}")
        else:
            logger.warning(f"[MySQL] 查询结果为空: {sql[:200]}")
        cursor.close()
        con.close()
        return str(result)
    except Exception as e:
        logger.error(f"[MySQL] 查询异常: {e}, SQL: {sql[:200]}")
        return f"查询异常: {e}"
