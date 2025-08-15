from typing import Optional, Literal
from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings


class MQConfig(BaseSettings):
    """
    MQ (Message Queue) 配置
    支持 RocketMQ 和 ONS (阿里云消息队列)
    """
    
    # 基础配置
    MQ_ENABLED: bool = Field(
        description="是否启用 MQ 功能",
        default=True,
    )
    
    MQ_ENVIRONMENT: Literal["local", "dev", "test", "testc", "pre", "pro", "oly", "ysld", "pg"] = Field(
        description="MQ 环境类型，影响使用 RocketMQ 还是 ONS",
        default="dev",
    )
    
    MQ_TOPIC: str = Field(
        description="MQ 主题名称",
        default="AI_PASS",
    )
    
    MQ_GROUP: str = Field(
        description="MQ 消费者组 ID",
        default="GID_AI_PASS",
    )
    
    MQ_NUM_WORKERS: PositiveInt = Field(
        description="MQ 消费者线程数量",
        default=10,
    )
    
    # RocketMQ 配置 (用于本地、开发、测试、预发环境)
    ROCKETMQ_ADDRESS: str = Field(
        description="RocketMQ NameServer 地址",
        default="rmqnamesrv:9876",
    )
    
    # ONS 配置 (用于生产环境)
    ONS_HOST: Optional[str] = Field(
        description="ONS HTTP 接入点",
        default=None,
    )
    
    ONS_ACCESS_ID: Optional[str] = Field(
        description="ONS AccessKey ID",
        default=None,
    )
    
    ONS_ACCESS_KEY: Optional[str] = Field(
        description="ONS AccessKey Secret",
        default=None,
    )
    
    ONS_INSTANCE_ID: Optional[str] = Field(
        description="ONS 实例 ID",
        default=None,
    )
    
    @property
    def is_rocketmq_env(self) -> bool:
        """判断是否为 RocketMQ 环境"""
        return self.MQ_ENVIRONMENT in ["local", "dev", "test", "testc", "pre"]
    
    @property
    def is_ons_env(self) -> bool:
        """判断是否为 ONS 环境"""
        return self.MQ_ENVIRONMENT in ["pro", "oly", "ysld", "pg"]
