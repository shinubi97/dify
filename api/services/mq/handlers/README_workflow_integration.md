# Dify 工作流 MQ 集成说明

## 概述

本集成实现了通过消息队列 (MQ) 执行 Dify 工作流的功能，直接调用 Dify 的核心工作流执行引擎，提供了高性能、可靠的工作流执行服务。

## 架构设计

### 方案选择
我们选择了**方案二：直接调用底层逻辑**，而不是 HTTP 接口调用。

**选择理由**：
1. **性能优势**：避免 HTTP 网络开销，直接调用核心服务
2. **架构一致性**：与 Dify 内部设计模式完全一致
3. **错误处理**：获得更详细的错误信息和状态控制
4. **扩展性**：更容易根据需要扩展功能

### 核心组件

```
MQ 消息 → WorkflowExecutionHandler → AppGenerateService → WorkflowAppGenerator → WorkflowEntry → GraphEngine
```

## 代码设计

### 1. API 密钥验证
**代码出处**: `api/controllers/service_api/wraps.py:validate_app_token`

```python
def _validate_api_key(self, api_key: str) -> tuple[App, ApiToken]:
    # 复用 Dify 原生的 API 密钥验证逻辑
    # 验证：令牌有效性、应用状态、API 服务启用状态、应用类型
```

### 2. 用户管理
**代码出处**: `api/controllers/service_api/wraps.py:create_or_update_end_user_for_user_id`

```python
def _get_or_create_end_user(self, app_model: App, user_id: Optional[str] = None) -> EndUser:
    # 复用 Dify 原生的终端用户创建逻辑
```

### 3. 工作流执行
**代码出处**: `api/controllers/service_api/app/workflow.py:WorkflowRunApi.post`

```python
response = AppGenerateService.generate(
    app_model=app_model,
    user=end_user,
    args=args,
    invoke_from=InvokeFrom.SERVICE_API,
    streaming=streaming
)
```

### 4. Flask 应用上下文处理
为了解决 MQ 消费者线程中 Flask 应用上下文缺失的问题，我们：

```python
def _execute_workflow_with_context(self, app_model: App, end_user: EndUser, args: Dict, streaming: bool):
    from app_factory import create_app
    app = create_app()
    
    with app.app_context():
        return AppGenerateService.generate(...)
```

## 使用方法

### 消息格式

向 MQ 发送如下格式的消息：

```json
{
    "requestId": "unique-request-id",
    "api_key": "app-xxxxxxxxxxxxxxxxxxxxxxxx",
    "inputs": {
        "text": "输入文本",
        "number": 123,
        "select": "option1"
    },
    "user": "user123",
    "response_mode": "blocking",
    "files": [],
    "workflow_id": "optional-workflow-id"
}
```

### 参数说明

- `requestId`: 唯一请求标识符
- `api_key`: Dify 应用的 API 密钥
- `inputs`: 工作流输入参数字典
- `user`: 用户标识（**必需**，与 HTTP API 保持一致）
- `response_mode`: 响应模式，"blocking" 或 "streaming"（默认 "blocking"）
- `files`: 文件列表（可选）
- `workflow_id`: 特定工作流 ID（可选，用于指定工作流版本）

**注意**: `user` 字段是必需的，与 Dify HTTP API 的要求完全一致。如果不提供会返回错误。

### 响应格式

成功响应：
```json
{
    "requestId": "unique-request-id",
    "status": 1,
    "msg": "工作流执行成功",
    "data": {
        "execution_id": "exec-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "outputs": {
            "result": "工作流输出结果",
            "message": "处理完成"
        }
    }
}
```

失败响应：
```json
{
    "requestId": "unique-request-id",
    "status": 0,
    "msg": "错误描述"
}
```

## 错误处理

代码实现了完整的错误分类处理：

1. **认证错误**: API 密钥无效
2. **权限错误**: 应用状态异常、API 服务被禁用
3. **资源错误**: 应用或工作流不存在
4. **模型服务错误**: 提供商令牌未初始化、配额超限
5. **调用错误**: 频率限制、调用失败
6. **系统错误**: 其他未预期的错误

## 测试示例

### 1. 基本工作流执行

```bash
# 发送测试消息到 MQ
{
    "requestId": "test-001",
    "api_key": "app-T24k5z2NTGABHCmYFhmz714k",
    "inputs": {
        "text": "Hello, World!",
        "number": 42
    },
    "user_id": "test_user"
}
```

### 2. 流式响应测试

```bash
{
    "requestId": "test-002",
    "api_key": "app-T24k5z2NTGABHCmYFhmz714k",
    "inputs": {
        "prompt": "生成一个故事"
    },
    "response_mode": "streaming",
    "user_id": "test_user"
}
```

### 3. 文件上传测试

```bash
{
    "requestId": "test-003",
    "api_key": "app-T24k5z2NTGABHCmYFhmz714k",
    "inputs": {
        "document": "文档内容"
    },
    "files": [
        {
            "type": "image",
            "transfer_method": "remote_url",
            "url": "https://example.com/image.jpg"
        }
    ],
    "user_id": "test_user"
}
```

## 部署注意事项

1. **依赖检查**: 确保所有 Dify 依赖项已正确安装
2. **数据库连接**: 确保数据库连接配置正确
3. **应用工厂**: 确保 `app_factory.py` 可正常导入
4. **权限配置**: 确保 MQ 服务有适当的数据库访问权限
5. **日志配置**: 建议启用详细日志以便调试

## 性能优化

1. **连接池**: 使用数据库连接池减少连接开销
2. **异步处理**: MQ 消费者本身就是异步的
3. **错误重试**: 可配置消息重试机制
4. **监控告警**: 建议添加执行时间和错误率监控

## 故障排除

### 常见问题

1. **应用上下文错误**: 确保正确导入 `app_factory.create_app`
2. **数据库连接错误**: 检查数据库连接配置和权限
3. **API 密钥错误**: 确认 API 密钥格式正确且应用存在
4. **工作流不存在**: 确认应用类型为 "workflow" 且已发布

### 调试方法

1. 启用详细日志记录
2. 检查 MQ 消息格式
3. 验证 API 密钥和应用状态
4. 测试工作流在 Web 界面是否正常工作

## 扩展功能

可以基于此基础实现：

1. **批量执行**: 支持批量工作流执行
2. **回调通知**: 执行完成后的回调机制
3. **执行监控**: 实时执行状态监控
4. **结果存储**: 执行结果的持久化存储
5. **优先级队列**: 基于优先级的工作流调度

## 总结

本集成方案完全符合 Dify 的原始设计模式，通过直接调用核心服务提供了高性能、可靠的工作流执行能力。代码实现遵循了 Dify 的最佳实践，确保了与核心功能的完全兼容性。
