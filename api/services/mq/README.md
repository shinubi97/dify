# Dify MQ 服务集成

## 概述

该 MQ 服务模块按照 Dify 的扩展架构模式实现，提供统一的消息队列功能，支持 RocketMQ 和阿里云 ONS。

## 架构设计

```
api/services/mq/
├── __init__.py
├── README.md                    # 本文档
├── mq_service.py               # MQ 服务主类
├── mq_startup.py               # 启动管理器
├── client/                     # MQ 客户端
│   ├── __init__.py
│   ├── mq_client.py           # 统一客户端接口
│   ├── rocketmq_client.py     # RocketMQ 客户端
│   └── ons_client.py          # ONS 客户端
└── handlers/                   # 消息处理器
    ├── __init__.py
    ├── base_handler.py        # 处理器基类
    └── workflow_execution_handler.py  # 工作流执行处理器
```

## 配置说明

在 `.env` 文件中添加以下配置：

```bash
# MQ 基础配置
MQ_ENABLED=true                 # 是否启用 MQ 功能
MQ_ENVIRONMENT=dev              # 环境类型：dev/test/pre (RocketMQ) 或 pro/oly (ONS)
MQ_TOPIC=AI_PASS               # MQ 主题名称
MQ_GROUP=GID_AI_PASS           # 消费者组 ID
MQ_NUM_WORKERS=10              # 消费者线程数

# RocketMQ 配置（开发/测试环境）
ROCKETMQ_ADDRESS=localhost:9876

# ONS 配置（生产环境）
ONS_HOST=http://xxx.mq-http.cn-hangzhou.aliyuncs.com
ONS_ACCESS_ID=your_access_id
ONS_ACCESS_KEY=your_access_key
ONS_INSTANCE_ID=your_instance_id
```

## 环境说明

- **RocketMQ 环境**: local, dev, test, testc, pre
- **ONS 环境**: pro, oly, ysld, pg

系统会根据 `MQ_ENVIRONMENT` 自动选择对应的客户端。

## 使用方式

### 1. 启动 MQ 服务

MQ 服务会在应用启动时自动初始化和启动（如果 `MQ_ENABLED=true`）。

### 2. 发送消息

```python
from extensions.ext_mq import mq_manager

# 发送消息
mq_manager.send_message(
    keys="test_key",
    tags="workflow_execution", 
    body='{"requestId":"123","app_id":"app_123","inputs":{}}'
)
```

### 3. 添加新的消息处理器

1. 继承 `BaseBizHandler` 创建新处理器：

```python
from services.mq.handlers.base_handler import BaseBizHandler

class CustomHandler(BaseBizHandler):
    @staticmethod
    def get_supported_tags():
        return ["custom_tag"]
    
    def _do_handle(self, data):
        # 处理逻辑
        return {"status": 1, "msg": "处理成功"}
```

2. 在 `mq_service.py` 的 `_init_handlers` 方法中注册：

```python
def _init_handlers(self):
    handlers = {}
    
    # 现有处理器
    workflow_handler = WorkflowExecutionHandler()
    for tag in workflow_handler.get_supported_tags():
        handlers[tag] = workflow_handler
    
    # 新增处理器
    custom_handler = CustomHandler()
    for tag in custom_handler.get_supported_tags():
        handlers[tag] = custom_handler
    
    return handlers
```

## 消息格式

### 标准消息格式

```json
{
    "requestId": "唯一请求ID",
    "app_id": "应用ID",
    "inputs": {},
    "user_id": "用户ID（可选）"
}
```

### 响应格式

```json
{
    "requestId": "请求ID",
    "status": 1,           // 1: 成功, 0: 失败
    "msg": "处理结果描述",
    "data": {}             // 具体数据（可选）
}
```

## 依赖库

### RocketMQ
```bash
pip install rocketmq-client-python
```

### ONS (阿里云)
```bash
pip install mq-http-sdk
```

## 监控和日志

- 所有 MQ 操作都会记录详细日志
- 支持消息处理时间统计
- 支持队列大小监控
- 支持优雅关闭和错误恢复

## 扩展特性

- ✅ 延迟初始化
- ✅ 配置驱动
- ✅ 条件启用/禁用
- ✅ 优雅启动/关闭
- ✅ 线程安全
- ✅ 错误处理和重试
- ✅ 消息路由
- ✅ 多环境支持

该实现完全符合 Dify 的扩展架构模式，可以无缝集成到现有系统中。