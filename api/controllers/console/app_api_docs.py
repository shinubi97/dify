
import flask_restful
from flask_login import current_user
from flask_restful import Resource, fields, marshal_with, reqparse
from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from libs.helper import TimestampField
from libs.login import login_required
from models.app_api_docs import AppApiDocs
from models.model import App

from . import api
from .wraps import account_initialization_required, setup_required

# 定义响应字段
app_api_docs_fields = {
    "id": fields.String,
    "tenant_id": fields.String,
    "app_id": fields.String,
    "app_mode": fields.String,
    "workflow_id": fields.String,
    "api_key": fields.String,
    "base_url": fields.String,
    "endpoints": fields.Raw,
    "curl_examples": fields.Raw,
    "python_examples": fields.Raw,
    "inputs_schema": fields.Raw,
    "outputs_schema": fields.Raw,
    "mock_data": fields.Raw,
    "mq_info": fields.Raw,
    "created_at": TimestampField,
    "updated_at": TimestampField,
    "created_by": fields.String,
    "updated_by": fields.String,
    # 添加 app 相关信息
    "app_name": fields.String,
    "app_description": fields.String,
    "app_icon": fields.String,
    "app_icon_background": fields.String,
}

app_api_docs_list_fields = {
    "data": fields.List(fields.Nested(app_api_docs_fields)),
    "total": fields.Integer,
    "page": fields.Integer,
    "limit": fields.Integer,
    "has_more": fields.Boolean,
}

app_api_docs_detail_fields = {
    "data": fields.Nested(app_api_docs_fields),
}

def _get_app_api_docs_with_app(doc_id, tenant_id):
    """Get app API documentation by ID and tenant with app information"""
    with Session(db.engine) as session:
        result = session.execute(
            select(AppApiDocs, App).join(
                App, AppApiDocs.app_id == App.id
            ).where(
                AppApiDocs.id == doc_id,
                AppApiDocs.tenant_id == tenant_id
            )
        ).first()
        
        if result is None:
            flask_restful.abort(404, message="API documentation not found.")
        
        return result

class AppApiDocsListApi(Resource):
    """API for listing app API documentation"""
    
    method_decorators = [account_initialization_required, login_required, setup_required]
    
    @marshal_with(app_api_docs_list_fields)
    def get(self):
        """Get app API documentation list with pagination and filtering"""
        
        parser = reqparse.RequestParser()
        parser.add_argument("page", type=int, default=1, location="args")
        parser.add_argument("limit", type=int, default=20, location="args")
        parser.add_argument("app_id", type=str, location="args")
        parser.add_argument("app_mode", type=str, location="args")
        parser.add_argument("keyword", type=str, location="args")
        parser.add_argument("sort_by", type=str, choices=["created_at", "-created_at", "updated_at", "-updated_at"], 
                          default="-created_at", location="args")
        
        args = parser.parse_args()
        
        # 分页参数
        page = args["page"]
        limit = min(args["limit"], 100)  # 限制最大每页数量
        
        with Session(db.engine) as session:
            # 构建基础查询（不包含排序和分页）
            base_query = select(AppApiDocs, App).join(
                App, AppApiDocs.app_id == App.id
            )
            
            # 只有当用户有租户ID时才进行租户过滤
            if current_user.current_tenant_id:
                base_query = base_query.where(AppApiDocs.tenant_id == current_user.current_tenant_id)
            
            # 应用过滤器到基础查询
            if args.get("app_id"):
                base_query = base_query.where(AppApiDocs.app_id == args["app_id"])
            
            if args.get("app_mode") and args["app_mode"] != "all":
                base_query = base_query.where(AppApiDocs.app_mode == args["app_mode"])
            
            if args.get("keyword"):
                base_query = base_query.where(App.name.ilike(f"%{args['keyword']}%"))
            
            # 获取总数
            total_query = select(db.func.count()).select_from(base_query.subquery())
            total = session.scalar(total_query)
            
            # 获取分页数据（在基础查询上添加排序和分页）
            offset = (page - 1) * limit
            
            # 根据排序参数构建最终查询
            if args["sort_by"] == "created_at":
                final_query = base_query.order_by(AppApiDocs.created_at.asc())
            elif args["sort_by"] == "-created_at":
                final_query = base_query.order_by(AppApiDocs.created_at.desc())
            elif args["sort_by"] == "updated_at":
                final_query = base_query.order_by(AppApiDocs.updated_at.asc())
            elif args["sort_by"] == "-updated_at":
                final_query = base_query.order_by(AppApiDocs.updated_at.desc())
            else:
                final_query = base_query.order_by(AppApiDocs.created_at.desc())
            
            query = final_query.offset(offset).limit(limit)
            results = session.execute(query).all()
            
            # 转换为字典格式
            docs_data = []
            for doc, app in results:
                doc_dict = doc.to_dict()
                # 直接使用 JOIN 查询到的 app 信息
                doc_dict["app_name"] = app.name
                doc_dict["app_description"] = app.description
                doc_dict["app_icon"] = app.icon
                doc_dict["app_icon_background"] = app.icon_background
                docs_data.append(doc_dict)
            
            return {
                "data": docs_data,
                "total": total,
                "page": page,
                "limit": limit,
                "has_more": (page * limit) < total
            }

class AppApiDocsDetailApi(Resource):
    """API for getting specific app API documentation"""
    
    method_decorators = [account_initialization_required, login_required, setup_required]
    
    @marshal_with(app_api_docs_detail_fields)
    def get(self, doc_id: str):
        """Get specific app API documentation by ID"""
        
        result = _get_app_api_docs_with_app(doc_id, current_user.current_tenant_id)
        doc, app = result
        
        # 直接使用 JOIN 查询到的信息
        doc_dict = doc.to_dict()
        doc_dict["app_name"] = app.name
        doc_dict["app_description"] = app.description
        doc_dict["app_icon"] = app.icon
        doc_dict["app_icon_background"] = app.icon_background
        
        return {"data": doc_dict}

class AppApiDocsByAppApi(Resource):
    """API for getting API documentation by app ID"""
    
    method_decorators = [account_initialization_required, login_required, setup_required]
    
    @marshal_with(app_api_docs_detail_fields)
    def get(self, app_id: str):
        """Get API documentation for a specific app"""
        
        with Session(db.engine) as session:
            # 使用 JOIN 查询获取 app 和 API 文档信息
            result = session.execute(
                select(AppApiDocs, App).join(
                    App, AppApiDocs.app_id == App.id
                ).where(
                    AppApiDocs.app_id == app_id,
                    AppApiDocs.tenant_id == current_user.current_tenant_id
                )
            ).first()
            
            if not result:
                flask_restful.abort(404, message="API documentation not found for this app")
            
            doc, app = result
            
            # 检查 app 是否属于当前租户
            if app.tenant_id != current_user.current_tenant_id:
                flask_restful.abort(404, message="App not found")
            
            # 直接使用 JOIN 查询到的信息
            doc_dict = doc.to_dict()
            doc_dict["app_name"] = app.name
            doc_dict["app_description"] = app.description
            doc_dict["app_icon"] = app.icon
            doc_dict["app_icon_background"] = app.icon_background
            
            return {"data": doc_dict}

# 注册路由
api.add_resource(AppApiDocsListApi, "/app-api-docs")
api.add_resource(AppApiDocsDetailApi, "/app-api-docs/<uuid:doc_id>")
api.add_resource(AppApiDocsByAppApi, "/apps/<uuid:app_id>/api-docs")
