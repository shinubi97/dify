import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ONSClient:
    """阿里云 ONS 客户端实现"""

    def __init__(self, host: str, access_id: str, access_key: str, instance_id: str):
        self.host = host
        self.access_id = access_id
        self.access_key = access_key
        self.instance_id = instance_id
        
        try:
            from mq_http_sdk.mq_client import MQClient
            from mq_http_sdk.mq_exception import MQExceptionBase
            from mq_http_sdk.mq_producer import TopicMessage
            
            self.MQClient = MQClient
            self.MQExceptionBase = MQExceptionBase
            self.TopicMessage = TopicMessage
            
        except ImportError as e:
            logger.error("ONS client library not found. Please install mq-http-sdk")
            raise ImportError("mq-http-sdk is required for ONS support") from e

    def _get_client(self):
        """获取 MQ 客户端"""
        return self.MQClient(self.host, self.access_id, self.access_key)

    def send_message(self, topic: str, keys: str, tags: str, body: str):
        """发送消息"""
        try:
            msg = self.TopicMessage(body, tags)
            msg.set_message_key(keys)
            client = self._get_client()
            producer = client.get_producer(self.instance_id, topic)
            return producer.publish_message(msg)
        except self.MQExceptionBase as e:
            logger.error(f"发送 ONS 消息失败: {e}")
            raise

    def subscribe(self, topic: str, group: str, callback: Callable, expression: str = "*"):
        """订阅消息"""
        client = self._get_client()
        consumer = client.get_consumer(self.instance_id, topic, group, expression)
        
        while True:
            try:
                success_recv_msgs = []
                # 批量消费消息
                for msg in consumer.consume_message(12, 3):
                    if callback(msg):
                        success_recv_msgs.append(msg)
                
                # 批量确认消息
                if success_recv_msgs:
                    receipt_handles = [msg.receipt_handle for msg in success_recv_msgs]
                    consumer.ack_message(receipt_handles)
                    
            except self.MQExceptionBase as e:
                if e.type == "MessageNotExist":
                    continue
                logger.error(f"ONS 消息消费失败: {e}")
                continue
            except Exception as e:
                logger.error(f"消息处理异常: {e}")
                continue

    def shutdown(self):
        """关闭客户端"""
        # ONS HTTP 客户端无需显式关闭
        logger.info("ONS client shutdown completed")
