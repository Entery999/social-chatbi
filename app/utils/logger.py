import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

#自定义的工具类，封装日志实例创建逻辑
class Logger:
    @classmethod
    def get_Logger(cls, name=__name__):
        #统一日志存放路径
        base_dir = Path(__file__).resolve().parent.parent
        #在对应的目录下拼接logs文件夹，用于存放日志
        log_dir = base_dir / 'logs'
        #创建日志文件夹
        log_dir.mkdir(exist_ok=True)
        #日志存放的具体文件路劲拼接
        log_file = log_dir / "app.log"

        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            #日志规范化输出
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] %(message)s')
            #创建控制台打印输出
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)

            #创建自动滚动文件日志处理器，将文件持久化写入本地文件，文件超出之后，自动进行分割备份
            file_handler = RotatingFileHandler(log_file,
                                               #10MB
                                               maxBytes=10*1024*1024,
                                               backupCount=10,
                                               encoding='utf-8'
                                               )
            file_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
        return logger
