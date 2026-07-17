from langchain.agents import AgentState
from langchain.agents.middleware import before_agent
from langgraph.runtime import Runtime
from langsmith.run_trees import configure

from app.utils.logger import Logger
from app.utils.permission_role import permission_role

logger = Logger().get_Logger(__name__)

def _get_user_id_from_runtime(runtime: Runtime):
    try:
        config = getattr(runtime, "config", None)
        logger.info(f"runtime config: {config}")
        if not config:
            return None
        if isinstance(config, dict):
            configurable = config.get("configurable", {}) or {}
            return configurable.get("user_id", None)
        configurable = getattr(config, "configurable", None)
        if isinstance(configurable, dict):
            return configurable.get("user_id")
        return None
    except Exception as e:
        logger.error(f"从runtime中获取user_id失败：{e}")
        return None

def _get_user_id_from_message(messages):
    try:
        if not messages:
            return None
        first_message = messages[0]
        if isinstance(first_message, dict):
            additional_kwargs = first_message.get("additional_kwargs", {}) or {}
            return additional_kwargs.get("user_id")
    except Exception as e:
        logger.warning(f"从messages获取user_id失败：{e}")
        return None

@before_agent()
def check_permission(agent: AgentState, runtime: Runtime):
    messages = agent.get("messages", [])
    if not messages:
        raise Exception("消息不能为空")
    user_id = _get_user_id_from_runtime(runtime)
    if not user_id:
        user_id = _get_user_id_from_message(messages)

    if not user_id:
        raise Exception("缺少用户的身份信息")
    logger.info(f"用户：{user_id}")
    role = permission_role(user_id)
    if role is None:
        raise Exception("用户不存在")
    if role == "查询失败":
        raise Exception("查询失败")
    allowed_role = ["总经理"]

    if role not in allowed_role:
        raise Exception(f"用户权限不足，当前角色为：{role}")
    logger.info(f"权限校验通过，当前角色为：{role}")
    return None









