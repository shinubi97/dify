import json
import logging
import uuid

from flask import Flask, current_app
from werkzeug.exceptions import Forbidden, NotFound, Unauthorized

# 复用 Dify 原始的验证逻辑
from controllers.service_api.wraps import FetchUserArg, WhereisUserArg, validate_app_token
from core.app.entities.app_invoke_entities import InvokeFrom
from core.errors.error import (
    ModelCurrentlyNotSupportError,
    ProviderTokenNotInitError,
    QuotaExceededError,
)
from core.model_runtime.errors.invoke import InvokeError
from models.model import App, AppMode, EndUser
from services.app_generate_service import AppGenerateService
from services.errors.app import WorkflowIdFormatError, WorkflowNotFoundError
from services.errors.llm import InvokeRateLimitError

from .base_handler import BaseBizHandler

logger = logging.getLogger(__name__)


class WorkflowExecutionHandler(BaseBizHandler):
    """工作流执行处理器 - 直接调用 Dify 工作流执行引擎"""

    def __init__(self, app: Flask = None):
        """初始化处理器，可选地传入 Flask 应用实例"""
        self.app = app

    @staticmethod
    def get_supported_tags() -> list[str]:
        return ["workflow_execution"]

    def validate_message(self, data: dict) -> dict:
        """验证工作流执行消息格式"""
        # 先执行基础验证
        base_result = super().validate_message(data)
        if not base_result["valid"]:
            return base_result

        # 工作流特定验证 - 遵循 HTTP API 的要求
        required_fields = ["api_key", "inputs", "user"]  # 添加 user 字段作为必需项
        for field in required_fields:
            if field not in data:
                return {"valid": False, "reason": f"缺少必需字段: {field}"}

        return {"valid": True, "reason": ""}

    @validate_app_token(fetch_user_arg=FetchUserArg(fetch_from=WhereisUserArg.JSON, required=True))
    def _execute_workflow_core(self, app_model: App, end_user: EndUser, inputs: dict, response_mode: str, files: list, workflow_id: str) -> dict:
        """核心工作流执行逻辑 - 直接使用 Dify 原始装饰器！"""
        # 检查应用类型
        app_mode = AppMode.value_of(app_model.mode)
        if app_mode != AppMode.WORKFLOW:
            raise Forbidden("App is not a workflow application")
        
        # 构建请求参数
        args = {
            "inputs": inputs,
            "files": files,
            "response_mode": response_mode,
        }
        
        # 如果指定了工作流 ID，添加到参数中
        if workflow_id:
            args["workflow_id"] = workflow_id
        
        # 执行工作流
        streaming = response_mode == "streaming"
        logger.info(f"开始执行工作流 - App ID: {app_model.id}, User: {end_user.session_id}, Streaming: {streaming}")
        
        response = AppGenerateService.generate(
            app_model=app_model,
            user=end_user,
            args=args,
            invoke_from=InvokeFrom.SERVICE_API,
            streaming=streaming
        )
        
        logger.info(f"工作流执行完成 - App ID: {app_model.id}, User: {end_user.session_id}, Streaming: {streaming}")
        
        # 处理响应并返回统一格式
        return self._process_response(response, streaming)
    
    def _execute_with_decorator_logic(self, api_key: str, user_id: str, inputs: dict, response_mode: str, files: list, workflow_id: str) -> dict:
        """使用装饰器逻辑执行工作流"""
        # 在测试请求上下文中调用被装饰的函数
        with current_app.test_request_context(
            headers={'Authorization': f'Bearer {api_key}'},
            json={'user': user_id},
            content_type='application/json'
        ):
            # 直接调用被装饰的函数，装饰器会自动处理所有验证和用户设置
            return self._execute_workflow_core(inputs=inputs, response_mode=response_mode, files=files, workflow_id=workflow_id)
    
    def _process_response(self, response, streaming: bool) -> dict:
        """处理工作流响应并返回统一格式"""
        if streaming:
            # 流式响应 - 收集所有事件
            outputs = {}
            execution_id = str(uuid.uuid4())
            
            try:
                for chunk in response:
                    if isinstance(chunk, dict):
                        # 提取最终输出
                        if chunk.get("event") == "workflow_finished":
                            outputs = chunk.get("data", {}).get("outputs", {})
                            execution_id = chunk.get("data", {}).get("id", execution_id)
                            break
                        elif chunk.get("event") == "node_finished":
                            # 也可以从节点完成事件中提取部分输出
                            node_data = chunk.get("data", {})
                            if node_data.get("node_type") == "end":
                                outputs.update(node_data.get("outputs", {}))
            except Exception as stream_error:
                logger.exception(f"处理流式响应时出错: {str(stream_error)}")
                outputs = {"error": "Stream processing error"}
            
            return {
                "status": 1,
                "msg": "工作流执行成功",
                "data": {
                    "execution_id": execution_id,
                    "outputs": outputs
                }
            }
        else:
            # 阻塞式响应
            if isinstance(response, dict):
                execution_id = response.get("workflow_run_id", str(uuid.uuid4()))
                outputs = response.get("data", {})
                
                return {
                    "status": 1,
                    "msg": "工作流执行成功", 
                    "data": {
                        "execution_id": execution_id,
                        "outputs": outputs
                    }
                }
            else:
                return {
                    "status": 0,
                    "msg": "未知的响应格式"
                }



    def _execute_all_in_context(self, api_key: str, inputs: dict, user_id: str, response_mode: str, files: list, workflow_id: str) -> dict:
        """在 Flask 应用上下文中执行所有操作（数据库查询 + 工作流执行）"""
        # 获取应用实例
        if self.app:
            app = self.app
        else:
            try:
                app = current_app._get_current_object()
            except RuntimeError:
                from app_factory import create_app
                app = create_app()
        
        with app.app_context():
            # 直接复用 validate_app_token 装饰器的完整逻辑并执行工作流！
            result = self._execute_with_decorator_logic(api_key, user_id, inputs, response_mode, files, workflow_id)
            logger.info(f"工作流执行完成: {result}")
            return result

    def _do_handle(self, data: dict) -> dict:
        """处理工作流执行请求"""
        logger.info(f"接收到工作流执行消息: {json.dumps(data, ensure_ascii=False)}")
        
        try:
            # 提取请求参数 - 与 HTTP API 保持一致
            api_key = data.get("api_key")
            inputs = data.get("inputs", {})
            user_id = data.get("user")  # 修改为 "user" 字段，与 HTTP API 一致
            response_mode = data.get("response_mode", "blocking")  # blocking 或 streaming
            files = data.get("files", [])
            workflow_id = data.get("workflow_id")  # 可选的特定工作流 ID
            
            # 在应用上下文中执行所有操作（包括数据库查询和工作流执行）
            return self._execute_all_in_context(api_key, inputs, user_id, response_mode, files, workflow_id)
            
        except Unauthorized as e:
            logger.exception(f"认证失败: {str(e)}")
            return {
                "status": 0,
                "msg": f"认证失败: {str(e)}"
            }
        except Forbidden as e:
            logger.exception(f"权限被拒绝: {str(e)}")
            return {
                "status": 0,
                "msg": f"权限被拒绝: {str(e)}"
            }
        except NotFound as e:
            logger.exception(f"资源未找到: {str(e)}")
            return {
                "status": 0,
                "msg": f"资源未找到: {str(e)}"
            }
        except (WorkflowNotFoundError, WorkflowIdFormatError) as e:
            logger.exception(f"工作流错误: {str(e)}")
            return {
                "status": 0,
                "msg": f"工作流错误: {str(e)}"
            }
        except (ProviderTokenNotInitError, ModelCurrentlyNotSupportError, QuotaExceededError) as e:
            logger.exception(f"模型服务错误: {str(e)}")
            return {
                "status": 0,
                "msg": f"模型服务错误: {str(e)}"
            }
        except (InvokeRateLimitError, InvokeError) as e:
            logger.exception(f"调用错误: {str(e)}")
            return {
                "status": 0,
                "msg": f"调用错误: {str(e)}"
            }
        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}", exc_info=True)
            return {
                "status": 0,
                "msg": f"工作流执行失败: {str(e)}"
            }
