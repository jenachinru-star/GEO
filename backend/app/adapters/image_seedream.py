"""
Seedream 生图适配器（火山方舟 ARK 接入）
- 使用 OpenAI 兼容接口调用，与现有文本适配器风格一致
- 配置项（.env）：
    SEEDREAM_API_KEY  = 火山方舟 API Key
    SEEDREAM_BASE_URL = https://ark.cn-beijing.volces.com/api/v3
    SEEDREAM_MODEL    = doubao-seedream-5-0-pro
"""
import logging
from openai import OpenAI
from app.adapters.image_base import BaseImageAdapter, ImageResult

logger = logging.getLogger(__name__)


class SeedreamImageAdapter(BaseImageAdapter):
    """Seedream 生图平台适配器（火山方舟 ARK）"""

    def __init__(self, api_key: str, base_url: str, model: str = "doubao-seedream-5-0-pro"):
        super().__init__(api_key, base_url, model)
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=120,
            max_retries=2,
        )

    def generate(self, prompt: str, **kwargs) -> ImageResult:
        """同步生成图片（阻塞直到完成）

        Args:
            prompt: 生图提示词
            **kwargs: width, height, n, response_format
        """
        if not self.is_configured():
            return ImageResult(
                success=False, status="failed",
                error_message="Seedream 未配置：请设置 SEEDREAM_API_KEY 和 SEEDREAM_BASE_URL"
            )

        width = kwargs.get("width", 1024)
        height = kwargs.get("height", 1024)
        n = kwargs.get("n", 1)
        size = f"{width}x{height}"

        try:
            logger.info(f"Seedream 生图: model={self.model}, size={size}, n={n}")
            response = self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size=size,
                n=n,
                response_format="url",
            )

            image_urls = [item.url for item in response.data if hasattr(item, 'url') and item.url]
            if not image_urls:
                return ImageResult(
                    success=False, status="failed",
                    error_message="Seedream 返回空图片列表",
                    raw_response=response.model_dump() if hasattr(response, 'model_dump') else None
                )

            logger.info(f"Seedream 生图成功: {len(image_urls)} 张")
            return ImageResult(
                success=True,
                image_urls=image_urls,
                status="succeeded",
                width=width,
                height=height,
                raw_response=response.model_dump() if hasattr(response, 'model_dump') else None
            )

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Seedream 生图失败: {error_msg}")
            return ImageResult(
                success=False, status="failed",
                error_message=error_msg
            )

    def generate_async(self, prompt: str, **kwargs) -> ImageResult:
        """异步提交生图任务

        Seedream 同步接口已足够快（5~30秒），这里直接走同步并包装为异步返回。
        如后续需要真正的异步任务轮询，可改调火山方舟的异步任务接口。
        """
        result = self.generate(prompt, **kwargs)
        result.task_id = None  # 同步模式无 task_id
        result.status = "succeeded" if result.success else "failed"
        return result

    def get_status(self, task_id: str) -> ImageResult:
        """查询异步生图任务状态

        当前使用同步生图，无 task_id 概念。此方法保留接口完整性。
        """
        return ImageResult(
            success=False, status="failed",
            error_message="当前使用同步生图模式，无需查询任务状态"
        )
