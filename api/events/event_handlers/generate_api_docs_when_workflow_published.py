import logging
import json
import uuid

from events.app_event import app_published_workflow_was_updated
from extensions.ext_database import db
from models.model import ApiToken
from flask import request

logger = logging.getLogger(__name__)


@app_published_workflow_was_updated.connect
def handle(sender, **kwargs):
    """Generate API documentation and MQ info when workflow is published."""
    app = sender
    published_workflow = kwargs.get("published_workflow")
    
    if not published_workflow or app.mode != "workflow":
        return
    
    try:
        _generate_api_docs_and_mq_info(app, published_workflow)
    except Exception as e:
        logger.error(f"Failed to generate API docs for workflow {published_workflow.id}: {str(e)}")


def _generate_api_docs_and_mq_info(app, workflow):
    """Generate API documentation and MQ information with mock data."""
    
    # 获取 API Key
    api_token = db.session.query(ApiToken).where(
        ApiToken.app_id == app.id,
        ApiToken.type == "app"
    ).first()
    
    if not api_token:
        logger.warning(f"No API key found for app {app.id}")
        return
    
    # 获取动态 base_url
    base_url = _get_dynamic_base_url(app)
    
    # 获取 workflow 输入参数
    workflow_inputs = _extract_workflow_inputs(workflow)
    
    # 生成 mock 数据
    mock_inputs = _generate_mock_inputs(workflow_inputs)
    
    # 生成 API 文档示例
    curl_example = _generate_curl_example(base_url, api_token.token, mock_inputs, workflow.id)
    python_example = _generate_python_example(base_url, api_token.token, mock_inputs, workflow.id)
    
     # 生成 MQ 信息
    mq_info = _generate_mq_info(workflow, api_token.token)
    
     # 准备保存到数据库的数据
    api_docs = {
        "tenant_id": app.tenant_id,
        "app_id": app.id,
        "app_mode": app.mode,  # 添加 app_mode
        "workflow_id": workflow.id,
        "api_key": api_token.token,
        "endpoints": f"{base_url}/v1/workflows/run",  # 添加 endpoints
        "curl_example": curl_example,
        "python_example": python_example,
        "inputs_schema": workflow_inputs,
        "outputs_schema": None,  # 添加 outputs_schema
        "mock_data": mock_inputs,
        "mq_info": mq_info
    }
    
    # 保存到数据库或缓存
    _save_api_docs(api_docs)
    
    logger.info(f"Generated API docs and MQ info for workflow {workflow.id}")
    logger.info(f"Generated API docs are as follows:\n{json.dumps(api_docs, ensure_ascii=False, indent=2)}")


def _get_dynamic_base_url(app):
    """Get dynamic base URL for the app."""
    try:
        from configs import dify_config
        from flask import request
        
        # 直接复制 Dify 的逻辑，但不添加 "/v1" 后缀
        base_url = dify_config.SERVICE_API_URL or request.host_url.rstrip("/")
        return base_url
        
    except Exception as e:
        logger.error(f"Failed to get base URL: {str(e)}")
        # 如果出错，回退到请求主机地址
        return request.host_url.rstrip("/")
        
    


def _extract_workflow_inputs(workflow):
    """Extract input parameters from workflow."""
    try:
        # 使用正确的字段：workflow.graph_dict
        workflow_graph = workflow.graph_dict
                
        # 查找 start 节点，它包含输入参数定义
        start_node = None
        for node in workflow_graph.get("nodes", []):
            if node.get("data", {}).get("type") == "start":
                start_node = node
                break
        
        if not start_node:
            logger.warning("No start node found in workflow")
            return []
        
        # 从 start 节点的 data.variables 中提取输入参数
        variables = start_node.get("data", {}).get("variables", [])
        
        # 转换为标准格式，保持所有原始字段
        input_schema = []
        for variable in variables:
            input_schema.append({
                "variable": variable.get("variable", ""),
                "label": variable.get("label", ""),
                "type": variable.get("type", "text-input"),
                "required": variable.get("required", False),
                "max_length": variable.get("max_length"),
                "options": variable.get("options", []),
                "allowed_file_upload_methods": variable.get("allowed_file_upload_methods", []),
                "allowed_file_types": variable.get("allowed_file_types", []),
                "allowed_file_extensions": variable.get("allowed_file_extensions", [])
            })
        
        return input_schema
        
    except Exception as e:
        logger.error(f"Failed to extract workflow inputs: {str(e)}")
        return []


def _generate_mock_inputs(input_schema):
    """Generate mock data based on input schema."""
    mock_inputs = {}
    
    for param in input_schema:
        param_name = param["variable"]
        param_type = param["type"]
        
        if param_type == "text-input":
            mock_inputs[param_name] = f"mock_short_text"
        elif param_type == "paragraph":
            mock_inputs[param_name] = f"mock_paragraph"
        elif param_type == "select":
            options = param.get("options", [])
            if options:
                mock_inputs[param_name] = options[0]  # 使用第一个选项
            else:
                mock_inputs[param_name] = "option1"
        elif param_type == "number":
            mock_inputs[param_name] = 666
        elif param_type == "file":
            # 对于文件类型，提供文件信息结构
            mock_inputs[param_name] = {
                "transfer_method": "(string) 传递方式，remote_url 图片地址 / local_file 上传文件",
                "upload_file_id": "(string) 上传文件 ID（仅当传递方式为 local_file 时）",
                "url": " (string) 图片地址（仅当传递方式为 remote_url 时）",
                "type": "支持类型：document/image/audio/video/custom"
            }
        elif param_type == "file-list":
            # 对于文件列表，提供文件信息数组
            mock_inputs[param_name] = [
                {
                    "transfer_method": "remote_url 图片地址",
                    "url": " (string) 图片地址（仅当传递方式为 remote_url 时）",
                    "type": "支持类型：document/image/audio/video/custom"
                },
                {
                    "transfer_method": "local_file 上传文件",
                    "upload_file_id": "(string) 上传文件 ID（仅当传递方式为 local_file 时）",
                    "type": "支持类型：document/image/audio/video/custom"
                }
            ]
        else:
            # 默认处理
            mock_inputs[param_name] = f"mock_{param_name}_value"
    
    return mock_inputs


def _generate_curl_example(base_url, api_key, mock_inputs, workflow_id):
    """Generate curl example."""
    return f"""curl -X POST '{base_url}/v1/workflows/{workflow_id}/run' \\
--header 'Authorization: Bearer {api_key}' \\
--header 'Content-Type: application/json' \\
--data-raw '{{
    "inputs": {json.dumps(mock_inputs, indent=2, ensure_ascii=False)},
    "user": "abc-123"
}}'"""


def _generate_python_example(base_url, api_key, mock_inputs, workflow_id):
    """Generate Python example."""
    return f"""import requests

url = "{base_url}/v1/workflows/{workflow_id}/run"
headers = {{
    "Authorization": "Bearer {api_key}",
    "Content-Type": "application/json"
}}
data = {{
    "inputs": {json.dumps(mock_inputs, indent=2, ensure_ascii=False)},
    "user": "abc-123"
}}

response = requests.post(url, headers=headers, json=data)
print(response.json())"""


def _generate_mq_info(workflow, api_key):
    """Generate MQ information."""
    return {
        "topic": "AI_PASS",
        "tag": "workflow_execution",
        "example_message": {
            "request_id": str(uuid.uuid4()),
            "api_key": api_key,
            "inputs": _generate_mock_inputs(_extract_workflow_inputs(workflow)),
            "user": "mq_triggered_user"
        }
    }


def _save_api_docs(api_docs):
    """Save API documentation to database."""
    try:
        from models.app_api_docs import AppApiDocs
        from libs.login import current_user
        
        # 获取用户ID（如果可用）
        user_id = None
        try:
            if hasattr(current_user, 'id'):
                user_id = current_user.id
        except:
            pass
        
        # 调用模型的 create_or_update 方法
        doc = AppApiDocs.create_or_update(
            tenant_id=api_docs["tenant_id"],
            app_id=api_docs["app_id"],
            app_mode=api_docs["app_mode"],
            api_key=api_docs["api_key"],
            endpoints=api_docs["endpoints"],
            workflow_id=api_docs.get("workflow_id"),
            curl_examples=api_docs.get("curl_example"),
            python_examples=api_docs.get("python_example"),
            inputs_schema=api_docs.get("inputs_schema"),
            outputs_schema=api_docs.get("outputs_schema"),
            mock_data=api_docs.get("mock_data"),
            mq_info=api_docs.get("mq_info"),
            user_id=user_id
        )
        
        logger.info(f"Successfully saved API docs to database for app {api_docs['app_id']}")
        return doc
        
    except Exception as e:
        logger.error(f"Failed to save API docs to database: {str(e)}")
        # 回退到日志记录
        logger.info(f"API docs (fallback to log): {json.dumps(api_docs, indent=2)}")
        return None