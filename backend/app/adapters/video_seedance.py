"""
Seedance 视频生成适配器（火山方舟 ARK 接入）
- 异步任务模式：提交任务 → 轮询状态 → 获取视频URL
- 配置项（.env）：
    SEEDANCE_API_KEY  = 火山方舟 API Key
    SEEDANCE_BASE_URL = https://ark.cn-beijing.volces.com/api/v3
    SEEDANCE_MODEL    = ep-xxxxxxxx（接入点ID）
"""
import logging
import httpx
from app.adapters.video_base import BaseVideoAdapter, VideoResult

logger = logging.getLogger(__name__)


class SeedanceVideoAdapter(BaseVideoAdapter):
    """Seedance 视频生成适配器（火山方舟 ARK）"""

    def __init__(self, api_key: str, base_url: str, model: str = ""):
        super().__init__(api_key, base_url, model)
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def generate_async(self, prompt: str, **kwargs) -> VideoResult:
        """异步提交视频生成任务

        Args:
            prompt: 视频描述提示词
            **kwargs: image_url（图生视频可选）, duration, resolution

        Returns:
            VideoResult: 包含 task_id，status=pending
        """
        if not self.is_configured():
            return VideoResult(
                success=False, status="failed",
                error_message="Seedance 未配置：请设置 SEEDANCE_API_KEY 和 SEEDANCE_BASE_URL"
            )

        # 构建 content
        content = [{"type": "text", "text": prompt}]

        # 图生视频：可选传入首帧图片
        image_url = kwargs.get("image_url")
        if image_url:
            content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })

        payload = {
            "model": self.model,
            "content": content,
        }

        try:
            url = f"{self.base_url}/contents/generations/tasks"
            logger.info(f"Seedance 提交视频任务: {url}, prompt={prompt[:50]}")

            resp = httpx.post(url, headers=self.headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            task_id = data.get("id")
            if not task_id:
                return VideoResult(
                    success=False, status="failed",
                    error_message=f"Seedance 返回无 task_id: {data}",
                    raw_response=data,
                )

            logger.info(f"Seedance 任务已提交: task_id={task_id}")
            return VideoResult(
                success=True,
                task_id=task_id,
                status="pending",
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"Seedance 提交失败: {error_msg}")
            return VideoResult(
                success=False, status="failed",
                error_message=error_msg,
            )
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Seedance 提交异常: {error_msg}")
            return VideoResult(
                success=False, status="failed",
                error_message=error_msg,
            )

    def get_status(self, task_id: str) -> VideoResult:
        """查询视频生成任务状态

        Args:
            task_id: 异步任务ID（cgt-xxx）

        Returns:
            VideoResult: 任务状态和视频URL
        """
        if not self.is_configured():
            return VideoResult(
                success=False, status="failed",
                error_message="Seedance 未配置"
            )

        try:
            url = f"{self.base_url}/contents/generations/tasks/{task_id}"
            resp = httpx.get(url, headers=self.headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            status = data.get("status", "unknown")
            logger.info(f"Seedance 任务状态: {task_id} = {status}")

            if status == "succeeded":
                video_url = data.get("content", {}).get("video_url", "")
                return VideoResult(
                    success=True,
                    task_id=task_id,
                    status="succeeded",
                    video_urls=[video_url] if video_url else [],
                    raw_response=data,
                )
            elif status == "failed":
                error = data.get("error", {}).get("message", "未知错误")
                return VideoResult(
                    success=False, task_id=task_id,
                    status="failed", error_message=error,
                    raw_response=data,
                )
            else:
                # running / queued
                return VideoResult(
                    success=True, task_id=task_id,
                    status=status,
                    raw_response=data,
                )

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"Seedance 查询失败: {error_msg}")
            return VideoResult(
                success=False, status="failed",
                error_message=error_msg,
            )
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Seedance 查询异常: {error_msg}")
            return VideoResult(
                success=False, status="failed",
                error_message=error_msg,
            )
