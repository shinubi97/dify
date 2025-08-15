import logging
from events.app_event import app_was_created
from extensions.ext_database import db
from models.model import ApiToken

logger = logging.getLogger(__name__)


@app_was_created.connect
def handle(sender, **kwargs):
    """Create API key when an app is created if it doesn't exist."""
    app = sender

    try:
        # 直接复制 BaseApiKeyListResource 的逻辑
        _create_api_key_for_app(app)
        
    except Exception as e:
        logger.error(f"Unexpected error in API key creation for app {app.id}: {str(e)}")


def _create_api_key_for_app(app):
    """Create API key using the exact same logic as BaseApiKeyListResource."""
    
    # 1. 检查是否已存在 API Key (复制自 BaseApiKeyListResource.get 逻辑)
    existing_keys = db.session.query(ApiToken).where(
        ApiToken.app_id == app.id,
        ApiToken.type == "app"
    ).all()
    
    if existing_keys:
        logger.info(f"API key already exists for app {app.id}, skipping creation")
        return
    

    # 2. 生成 API Key (复制自 BaseApiKeyListResource.post 逻辑)
    key = ApiToken.generate_api_key("app-", 24)  # 复制自 AppApiKeyListResource.token_prefix
    
    # 3. 创建 ApiToken 实例 (复制自 BaseApiKeyListResource.post 逻辑)
    api_token = ApiToken()
    api_token.app_id = app.id
    api_token.tenant_id = app.tenant_id
    api_token.token = key
    api_token.type = "app"
    
    # 5. 保存到数据库 (复制自 BaseApiKeyListResource.post 逻辑)
    db.session.add(api_token)
    db.session.commit()
    
    logger.info(f"Successfully created API key for app {app.id}")
    return api_token
