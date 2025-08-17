import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


class RocketMQClient:
    """RocketMQ 客户端实现"""

    def __init__(self, group_id: str, address: str):
        self.group_id = group_id
        self.address = address
        self.consumer_is_shutdown = False
        
        try:
            from rocketmq.client import Message as ClientMessage
            from rocketmq.client import Producer, PushConsumer
            self.Producer = Producer
            self.ClientMessage = ClientMessage
            self.PushConsumer = PushConsumer
            
            self.producer = self._create_producer()
            self.consumer = self._create_consumer()
            
        except ImportError as e:
            logger.exception("RocketMQ client library not found. Please install rocketmq-client-python")
            raise ImportError("rocketmq-client-python is required for RocketMQ support") from e

    def _create_producer(self):
        """创建生产者"""
        producer = self.Producer(self.group_id)
        producer.set_namesrv_addr(self.address)
        producer.start()
        return producer

    def _create_consumer(self):
        """创建消费者"""
        consumer = self.PushConsumer(self.group_id)
        consumer.set_namesrv_addr(self.address)
        return consumer

    def send_message(self, topic: str, keys: str, tags: str, body: str):
        """发送消息"""
        msg = self.ClientMessage(topic)
        msg.set_keys(keys)
        msg.set_tags(tags)
        msg.set_body(body)
        return self.producer.send_sync(msg)

    def subscribe(self, topic: str, group: str, callback: Callable, expression: str = "*"):
        """订阅消息"""
        def rocket_callback_wrapper(msg):
            """包装回调函数，处理返回值"""
            result = callback(msg)
            # 如果回调返回 False，抛出异常触发重试机制
            if not result:
                raise Exception(f"消息处理失败，需要重试 topic={topic}, tag={msg.tags}")
            return result

        self.consumer.subscribe(topic, rocket_callback_wrapper, expression)
        self.consumer.start()
        
        # 保持消费者运行
        while not self.consumer_is_shutdown:
            import time
            time.sleep(1)

    def shutdown(self):
        """关闭客户端"""
        if hasattr(self, 'producer'):
            self.producer.shutdown()
        if hasattr(self, 'consumer'):
            self.consumer.shutdown()
        self.consumer_is_shutdown = True
