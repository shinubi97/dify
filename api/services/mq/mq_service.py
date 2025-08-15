import json
import logging
import queue
import threading
import time
from typing import Dict, List

from .client.mq_client import MQClient
from .handlers.base_handler import BaseBizHandler
from .handlers.workflow_execution_handler import WorkflowExecutionHandler

logger = logging.getLogger(__name__)


class MQService:
    """
    MQ 服务主类
    采用单例模式，管理消息队列的完整生命周期
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, topic: str, group: str, num_workers: int = 10, app=None):
        if self._initialized:
            return
            
        self.topic = topic
        self.group = group
        self.num_workers = num_workers
        self.app = app  # 保存 Flask 应用实例
        
        # 初始化 MQ 客户端
        self.mq_client = MQClient(topic=topic, group=group)
        
        # 线程控制
        self._running = False
        self._consumer_threads: List[threading.Thread] = []
        
        # 消息队列
        self.message_queue: queue.Queue = queue.Queue(maxsize=1000)
        
        # 初始化消息处理器
        self.handlers = self._init_handlers()
        
        self._initialized = True
        logger.info(f"MQService 初始化完成，Topic: {topic}, Group: {group}")
    
    def _init_handlers(self) -> Dict[str, BaseBizHandler]:
        """初始化消息处理器"""
        handlers = {}
        
        # 注册工作流执行处理器，传入 Flask 应用实例
        workflow_handler = WorkflowExecutionHandler(app=self.app)
        for tag in workflow_handler.get_supported_tags():
            handlers[tag] = workflow_handler
        
        # 在这里可以添加更多处理器
        # handlers.update(self._register_other_handlers())
        
        logger.info(f"已注册 {len(handlers)} 个消息处理器: {list(handlers.keys())}")
        return handlers
    
    def _route_handler(self, tag: str) -> BaseBizHandler:
        """根据标签路由到对应的处理器"""
        if isinstance(tag, bytes):
            tag = tag.decode('utf-8')
        
        # 如果只有一个处理器，直接返回
        if len(self.handlers) == 1:
            return next(iter(self.handlers.values()))
        
        # 按标签匹配
        handler = self.handlers.get(tag)
        if handler:
            return handler
        
        # 如果找不到对应处理器，使用默认处理器或抛出异常
        logger.warning(f"未找到标签 '{tag}' 对应的处理器")
        return next(iter(self.handlers.values()))  # 返回第一个处理器作为默认
    
    def _process_message(self, msg_tag: str, msg_body: str):
        """处理单条消息"""
        start_time = time.time()
        
        try:
            # 解析消息体
            data = json.loads(msg_body)
            logger.info(f"接收到消息 tag={msg_tag}: {data}")
            
            # 路由到对应处理器
            handler = self._route_handler(msg_tag)
            
            # 处理消息
            result = handler.handle(data)
            
            logger.info(f"消息处理完成 tag={msg_tag}, 耗时: {time.time()-start_time:.2f}s, 结果: {result}")
            
        except Exception as e:
            logger.error(f"消息处理异常 tag={msg_tag}: {str(e)}", exc_info=True)
    
    def _consumer_worker(self):
        """消费者线程工作函数"""
        worker_id = threading.current_thread().name
        logger.info(f"消费者线程 {worker_id} 启动")
        
        while self._running:
            try:
                # 从队列中获取消息
                msg_tag, msg_body = self.message_queue.get(timeout=1)
                
                try:
                    self._process_message(msg_tag, msg_body)
                except Exception as e:
                    logger.error(f"处理消息失败: {str(e)}")
                finally:
                    self.message_queue.task_done()
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"消费者线程异常: {str(e)}")
        
        logger.info(f"消费者线程 {worker_id} 退出")
    
    def start(self):
        """启动 MQ 服务"""
        with self._lock:
            if self._running:
                logger.warning("MQ服务已在运行中")
                return
            
            self._running = True
        
        # 启动消费者线程
        for i in range(self.num_workers):
            t = threading.Thread(
                target=self._consumer_worker,
                name=f"MQ-Consumer-{i}",
                daemon=True
            )
            t.start()
            self._consumer_threads.append(t)
        
        # 消息回调函数
        def message_callback(msg_tag: str, msg_body: str) -> bool:
            try:
                # 将消息放入队列
                self.message_queue.put((msg_tag, msg_body), block=True, timeout=5)
                logger.debug(f"消息加入队列 tag={msg_tag}, 队列大小: {self.message_queue.qsize()}")
                return True
            except queue.Full:
                logger.error(f"消息队列已满，丢弃消息 tag={msg_tag}")
                return False
            except Exception as e:
                logger.error(f"加入消息队列失败: {str(e)}")
                return False
        
        # 构建订阅表达式
        supported_tags = list(self.handlers.keys())
        expression = "||".join(supported_tags) if supported_tags else "*"
        
        # 启动订阅线程
        subscribe_thread = threading.Thread(
            target=self.mq_client.subscribe,
            args=(message_callback, expression),
            daemon=True,
            name="MQ-Subscriber"
        )
        subscribe_thread.start()
        
        logger.info(f"MQ服务启动完成，Topic: {self.topic}, Group: {self.group}")
        logger.info(f"监听标签: {expression}, 消费者线程数: {self.num_workers}")
    
    def shutdown(self):
        """关闭 MQ 服务"""
        with self._lock:
            if not self._running:
                logger.warning("MQ服务未运行")
                return
            
            logger.info("正在关闭MQ服务...")
            self._running = False
        
        # 等待队列中的消息处理完毕
        try:
            self.message_queue.join()
            logger.info("队列中的消息已处理完毕")
        except Exception as e:
            logger.warning(f"等待队列处理完毕时出错: {str(e)}")
        
        # 等待消费者线程退出
        for i, thread in enumerate(self._consumer_threads):
            try:
                thread.join(timeout=2)
                if thread.is_alive():
                    logger.warning(f"消费者线程 {i} 未能在超时时间内退出")
            except Exception as e:
                logger.warning(f"等待消费者线程 {i} 退出时出错: {str(e)}")
        
        # 关闭 MQ 客户端
        try:
            self.mq_client.shutdown()
        except Exception as e:
            logger.error(f"关闭MQ客户端时出错: {str(e)}")
        
        logger.info("MQ服务已关闭")
    
    def send_message(self, keys: str, tags: str, body: str):
        """发送消息"""
        return self.mq_client.send_message(keys, tags, body)
