import logging
from collections.abc import Callable
from typing import Optional

from configs import dify_config

logger = logging.getLogger(__name__)


class MQClient:
    """
    统一的 MQ 客户端接口
    根据环境自动选择 RocketMQ 或 ONS
    """

    def __init__(self, topic: str, group: str):
        self.topic = topic
        self.group = group
        self._client: Optional[RocketMQClient | ONSClient] = None
        self._initialize_client()

    def _initialize_client(self):
        """根据环境初始化对应的客户端"""
        try:
            if dify_config.is_rocketmq_env:
                from .rocketmq_client import RocketMQClient
                self._client = RocketMQClient(
                    group_id=self.group,
                    address=dify_config.ROCKETMQ_ADDRESS
                )
                logger.info(f"当前环境 {dify_config.MQ_ENVIRONMENT}，初始化 RocketMQ 客户端")
                
            elif dify_config.is_ons_env:
                from .ons_client import ONSClient
                self._client = ONSClient(
                    host=dify_config.ONS_HOST,
                    access_id=dify_config.ONS_ACCESS_ID,
                    access_key=dify_config.ONS_ACCESS_KEY,
                    instance_id=dify_config.ONS_INSTANCE_ID
                )
                logger.info(f"当前环境 {dify_config.MQ_ENVIRONMENT}，初始化 ONS 客户端")
            else:
                raise ValueError(f"Unsupported MQ environment: {dify_config.MQ_ENVIRONMENT}")
                
        except Exception as e:
            logger.exception(f"Failed to initialize MQ client: {e}")
            raise

    def send_message(self, keys: str, tags: str, body: str) -> any:
        """发送消息"""
        if not self._client:
            raise RuntimeError("MQ client is not initialized")
            
        result = self._client.send_message(self.topic, keys, tags, body)
        logger.info(f"当前环境 {dify_config.MQ_ENVIRONMENT}，发送消息成功: {result}")
        return result

    def subscribe(self, callback: Callable, expression: str = "*"):
        """订阅消息"""
        if not self._client:
            raise RuntimeError("MQ client is not initialized")
            
        def wrapped_callback(msg):
            """统一回调接口，确保返回消息 tag 和消息体"""
            try:
                # 处理不同类型的消息对象
                if hasattr(msg, 'message_body') and hasattr(msg, 'message_tag'):
                    # ONS 消息
                    return callback(msg.message_tag, msg.message_body)
                elif hasattr(msg, 'body') and hasattr(msg, 'tags'):
                    # RocketMQ 消息
                    return callback(msg.tags, msg.body)
                else:
                    logger.warning(f"Unknown message type: {type(msg)}")
                    return True
            except Exception as e:
                logger.exception(f"Error in message callback: {e}")
                return False
        
        self._client.subscribe(self.topic, self.group, wrapped_callback, expression)

    def shutdown(self):
        """关闭客户端"""
        if self._client:
            self._client.shutdown()
            logger.info("MQ client shutdown completed")
