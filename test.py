import logging

"""
DEBUG:通常用于诊断信息
INFO:普通消息，标识系统正常工作
WARNING:警告消息，可能存在问题
ERROR:错误信息，表示程序出错
CRITICAL:严重错误信息，表示致命问题，通常程序会直接崩溃
"""
#时间、日期、详细信息
logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(levelname)s: %(message)s')
#日志的使用，低等级可以打印高等级，反之不可以
logging.info("调试信息")
# logging.warning("这是调试信息")
# logging.debug("这是调试信息")
# logging.error("这是调试信息")