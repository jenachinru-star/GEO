"""文件上传 API - 支持图片上传到本地存储

功能：
- 图片上传（头像、文章配图等）
- 文件大小限制 10MB
- 支持 jpg/jpeg/png/gif/webp 格式
- 文件名随机生成，避免冲突
- 静态文件访问：/uploads/xxx.jpg
"""
import os
import uuid
import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from app.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/upload", tags=["文件上传"])

# 上传目录配置
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 允许的文件类型
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}

# 文件大小限制（10MB）
MAX_FILE_SIZE = 10 * 1024 * 1024


def get_file_extension(content_type: str, filename: str) -> str:
    """根据 content_type 或文件名获取扩展名"""
    if content_type in ALLOWED_IMAGE_TYPES:
        return ALLOWED_IMAGE_TYPES[content_type]
    # 从文件名提取扩展名
    _, ext = os.path.splitext(filename)
    if ext.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        return ext.lower()
    return ""


@router.post("/image", summary="上传图片")
async def upload_image(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
):
    """上传图片文件

    返回文件访问 URL，可用于头像、文章配图等
    """
    # 检查文件大小
    file_size = 0
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(status_code=400, detail="文件为空")

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制（最大 {MAX_FILE_SIZE // 1024 // 1024}MB）")

    # 检查文件类型
    ext = get_file_extension(file.content_type or "", file.filename or "")
    if not ext:
        raise HTTPException(status_code=400, detail="不支持的文件类型，仅支持 jpg/jpeg/png/gif/webp")

    # 生成随机文件名
    random_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, random_filename)

    # 保存文件
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"保存文件失败: {e}")
        raise HTTPException(status_code=500, detail="文件保存失败")

    # 返回文件访问 URL
    # 静态文件通过 /uploads/ 路径访问
    file_url = f"/uploads/{random_filename}"

    logger.info(f"用户 {user_id} 上传图片: {file.filename} -> {random_filename} ({file_size} bytes)")

    return {
        "code": 0,
        "message": "上传成功",
        "data": {
            "url": file_url,
            "filename": random_filename,
            "original_filename": file.filename,
            "size": file_size,
            "content_type": file.content_type,
        }
    }


def mount_static_files(app):
    """挂载静态文件服务（在 main.py 中调用）

    让上传的文件可以通过 /uploads/ 路径访问
    """
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
    logger.info(f"静态文件服务已挂载: /uploads -> {UPLOAD_DIR}")
