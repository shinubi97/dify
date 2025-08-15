import logging
from typing import Optional

from configs import dify_config
from dify_app import DifyApp

logger = logging.getLogger(__name__)


class MQManager:
    """
    MQ 管理器，模仿 RedisClientWrapper 的设计模式
    提供延迟初始化和优雅的服务管理
    """

    def __init__(self):
        self._service = None

    def initialize(self, service):
        """初始化 MQ 服务"""
        if self._service is None:
            self._service = service

    def __getattr__(self, item):
        if self._service is None:
            raise RuntimeError("MQ service is not initialized. Call init_app first.")
        return getattr(self._service, item)


# 全局 MQ 管理器实例
mq_manager = MQManager()


def is_enabled() -> bool:
    """检查 MQ 是否启用"""
    return dify_config.MQ_ENABLED


def init_app(app: DifyApp):
    """
    初始化 MQ 扩展
    按照 Dify 扩展模式进行初始化
    """
    global mq_manager
    
    if not is_enabled():
        logger.info("MQ service is disabled, skipping initialization")
        return

    try:
        # 延迟导入避免循环依赖
        from services.mq.mq_service import MQService
        
        # 创建 MQ 服务实例，传入 Flask 应用实例
        mq_service = MQService(
            topic=dify_config.MQ_TOPIC,
            group=dify_config.MQ_GROUP,
            num_workers=dify_config.MQ_NUM_WORKERS,
            app=app  # 传入 Flask 应用实例
        )
        
        # 初始化管理器
        mq_manager.initialize(mq_service)
        
        # 注册到 Flask 应用扩展
        app.extensions["mq"] = mq_manager
        
        logger.info("MQ extension initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize MQ extension: {e}")
        # 根据配置决定是否抛出异常
        if dify_config.DEBUG:
            raise
