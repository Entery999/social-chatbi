import os
import pymysql
import ssl
from dotenv import load_dotenv
from app.utils.logger import Logger

logger = Logger().get_Logger()

load_dotenv()

_ssl_ctx = ssl.create_default_context()

def permission_role(user_id: str) -> str:
    sql = "select role from user_info where email = %s"
    host = os.getenv("MYSQL_HOST")
    port = os.getenv("MYSQL_PORT")
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    database = os.getenv("MYSQL_DB")

    if not all([host, port, user, password, database]):
        logger.info("数据库配置不全，检查.env配置文件")
        return "查询失败"

    try:
        kwargs = dict(host=host, port=int(port), user=user, password=password, database=database)
        if "aivencloud" in (host or ""):
            kwargs["ssl"] = {"ssl": _ssl_ctx}
        con = pymysql.connect(**kwargs)
        cursor = con.cursor()
        try:
            cursor.execute(sql, (user_id,))
            result = cursor.fetchall()
            if result:
                role = result[0][0]
                logger.info(f"角色：{role}")
                return role
            return "None"
        except Exception as e:
            logger.info(f"角色查询失败：{e}")
            return "查询失败"
        finally:
            cursor.close()
            con.close()
    except Exception as e:
        logger.warning(f"数据库连接失败：{e}")
        return "查询失败"

if __name__ == "__main__":
    rs =permission_role("2623861451@qq.com")
    print(rs)



