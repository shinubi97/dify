# api/models/app_api_docs.py
from datetime import datetime
from typing import Dict, Any, List, Optional

import sqlalchemy as sa
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from libs.datetime_utils import naive_utc_now


from .base import Base
from models.types import StringUUID

from .engine import db



class AppApiDocs(Base):
    """
    Application API Documentation table.
    
    Stores API documentation for all app modes (completion, workflow, chat, advanced-chat, agent-chat).
    """
    
    __tablename__ = "app_api_docs"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="app_api_docs_pkey"),
        sa.Index("idx_app_api_docs_tenant_app", "tenant_id", "app_id"),
        sa.Index("idx_app_api_docs_app_mode", "app_mode"),
        sa.Index("idx_app_api_docs_workflow", "workflow_id"),
        sa.Index("idx_app_api_docs_api_key", "api_key"),
        sa.Index("idx_app_api_docs_created_at", "created_at"),
        sa.Index("idx_app_api_docs_updated_at", "updated_at"),
    )
    
    id: Mapped[str] = mapped_column(StringUUID, server_default=sa.text("uuid_generate_v4()"))
    tenant_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    app_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    app_mode: Mapped[str] = mapped_column(String(50), nullable=False)  # completion, workflow, chat, advanced-chat, agent-chat
    workflow_id: Mapped[Optional[str]] = mapped_column(StringUUID, nullable=True)  # 仅 workflow 模式需要
    
    # API 配置
    api_key: Mapped[str] = mapped_column(String(255), nullable=False)
    endpoints: Mapped[str] = mapped_column(String(255), nullable=False)  # 不同模式的端点配置
    
    # API 文档示例
    curl_examples: Mapped[Optional[str]] = mapped_column(sa.TEXT, nullable=True)
    python_examples: Mapped[Optional[str]] = mapped_column(sa.TEXT, nullable=True)
    
    # 输入输出模式
    inputs_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    outputs_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    mock_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # MQ 配置
    mq_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # 审计字段
    created_by: Mapped[str] = mapped_column(StringUUID, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_by: Mapped[Optional[str]] = mapped_column(StringUUID)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=naive_utc_now(),
        server_onupdate=func.current_timestamp(),
    )
    
    @classmethod
    def create_or_update(
        cls,
        tenant_id: str,
        app_id: str,
        app_mode: str,
        api_key: str,
        endpoints: str,
        workflow_id: Optional[str] = None,
        curl_examples: Optional[str] = None,
        python_examples: Optional[str] = None,
        inputs_schema: Optional[Dict[str, Any]] = None,
        outputs_schema: Optional[Dict[str, Any]] = None,
        mock_data: Optional[Dict[str, Any]] = None,
        mq_info: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> "AppApiDocs":
        """Create or update API documentation."""
        # 查找现有记录
        existing_doc = db.session.query(cls).where(
            cls.tenant_id == tenant_id,
            cls.app_id == app_id
        ).first()
        
        if existing_doc:
            # 更新现有记录
            existing_doc.app_mode = app_mode
            existing_doc.workflow_id = workflow_id
            existing_doc.api_key = api_key
            existing_doc.endpoints = endpoints
            existing_doc.curl_examples = curl_examples
            existing_doc.python_examples = python_examples
            existing_doc.inputs_schema = inputs_schema
            existing_doc.outputs_schema = outputs_schema
            existing_doc.mock_data = mock_data
            existing_doc.mq_info = mq_info
            existing_doc.updated_by = user_id
            existing_doc.updated_at = func.current_timestamp()
            db.session.commit()
            
            return existing_doc
        else:
            # 创建新记录
            new_doc = cls(
                tenant_id=tenant_id,
                app_id=app_id,
                app_mode=app_mode,
                workflow_id=workflow_id,
                api_key=api_key,
                endpoints=endpoints,
                curl_examples=curl_examples,
                python_examples=python_examples,
                inputs_schema=inputs_schema,
                outputs_schema=outputs_schema,
                mock_data=mock_data,
                mq_info=mq_info,
                created_by=user_id,
                updated_by=user_id
            )
            db.session.add(new_doc)
            db.session.commit()
            return new_doc
    
    @classmethod
    def get_by_app_id(cls, tenant_id: str, app_id: str) -> Optional["AppApiDocs"]:
        """Get API documentation by app ID."""
        return db.session.query(cls).where(
            cls.tenant_id == tenant_id,
            cls.app_id == app_id
        ).first()
    
    @classmethod
    def get_list_by_tenant(
        cls,
        tenant_id: str,
        page: int = 1,
        per_page: int = 20,
        app_mode: Optional[str] = None,
        app_id: Optional[str] = None
    ) -> tuple[List["AppApiDocs"], int]:
        """Get paginated list of API documentation."""
        query = db.session.query(cls).where(cls.tenant_id == tenant_id)
        
        if app_mode:
            query = query.where(cls.app_mode == app_mode)
        if app_id:
            query = query.where(cls.app_id == app_id)
        
        total_count = query.count()
        docs_list = query.order_by(cls.updated_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        return docs_list, total_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "app_id": str(self.app_id),
            "app_mode": self.app_mode,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "api_key": self.api_key,
            "endpoints": self.endpoints,
            "curl_examples": self.curl_examples,
            "python_examples": self.python_examples,
            "inputs_schema": self.inputs_schema,
            "outputs_schema": self.outputs_schema,
            "mock_data": self.mock_data,
            "mq_info": self.mq_info,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }
    