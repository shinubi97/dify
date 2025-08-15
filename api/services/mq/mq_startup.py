import atexit
import logging
import signal
import sys
from typing import Optional

logger = logging.getLogger(__name__)


class MQStartupManager:
    """
    MQ 启动管理器
    负责在应用启动时启动 MQ 服务，并在应用关闭时优雅地关闭服务
    """
    
    def __init__(self):
        self.mq_service: Optional['MQService'] = None
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """设置信号处理器，确保优雅关闭"""
        def signal_handler(signum, frame):
            logger.info(f"接收到信号 {signum}，正在关闭 MQ 服务...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 注册退出处理器
        atexit.register(self.shutdown)
    
    def start_mq_service(self, app):
        """启动 MQ 服务"""
        try:
            if hasattr(app, 'extensions') and 'mq' in app.extensions:
                self.mq_service = app.extensions['mq']
                self.mq_service.start()
                logger.info("MQ 服务启动成功")
            else:
                logger.warning("MQ 扩展未找到，跳过启动")
        except Exception as e:
            logger.error(f"启动 MQ 服务失败: {e}")
            if app.config.get('DEBUG'):
                raise
    
    def shutdown(self):
        """关闭 MQ 服务"""
        if self.mq_service:
            try:
                self.mq_service.shutdown()
                logger.info("MQ 服务已关闭")
            except Exception as e:
                logger.error(f"关闭 MQ 服务时出错: {e}")


# 全局实例
mq_startup_manager = MQStartupManager()
