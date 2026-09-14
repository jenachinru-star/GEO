from fastapi import APIRouter, Depends
from app.config import settings
from app.deps import get_current_user_id

router = APIRouter(prefix="/api/v1/tools", tags=["工具配置"])


@router.get("/config", summary="获取创作工具配置")
def get_tools_config(user_id: int = Depends(get_current_user_id)):
    return {
        "code": 0,
        "message": "success",
        "data": {
            "article_tool_url": settings.ARTICLE_TOOL_URL,
            "video_tool_url": settings.VIDEO_TOOL_URL,
            "publish_platforms": [
                {"code": "wechat", "name": "微信公众号"},
                {"code": "xiaohongshu", "name": "小红书"},
                {"code": "zhihu", "name": "知乎"},
                {"code": "video", "name": "视频号"},
                {"code": "douyin", "name": "抖音"},
                {"code": "other", "name": "其他"}
            ]
        }
    }
