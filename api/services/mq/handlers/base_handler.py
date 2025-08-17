import logging
import uuid
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseBizHandler(ABC):
    """业务处理器基类"""

    def handle(self, data: dict) -> dict:
        """处理消息的主方法"""
        request_id = data.get("requestId", str(uuid.uuid4()))
        
        try:
            # 验证消息格式
            validation_result = self.validate_message(data)
            if not validation_result["valid"]:
                return {
                    "requestId": request_id,
                    "status": 0,
                    "msg": f"消息验证失败: {validation_result['reason']}"
                }

            # 执行实际处理逻辑
            result = self._do_handle(data)

            return {
                "request_id": request_id,
                **result
            }
            
        except Exception as e:
            logger.error(f"业务处理失败: {str(e)}", exc_info=True)
            return {
                "request_id": request_id,
                "status": 0,
                "msg": str(e)
            }

    def validate_message(self, data: dict) -> dict:
        """
        验证消息格式是否符合当前处理器要求
        返回: {"valid": True/False, "reason": "错误原因"}
        """

        if "request_id" not in data:
            return {"valid": False, "reason": "request_id"}

        # 子类可以重写此方法添加特定验证
        return {"valid": True, "reason": ""}

    @abstractmethod
    def _do_handle(self, data: dict) -> dict:
        """
        实际的消息处理逻辑，子类必须实现
        """
        pass

    @staticmethod
    @abstractmethod
    def get_supported_tags() -> list[str]:
        """返回处理器支持的标签列表，子类必须实现"""
        pass
