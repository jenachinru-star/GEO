"""
Seedream 生图适配器（框架）
- 未配置 API Key 时返回明确错误
- API 调用逻辑用 TODO 标注，待配置后实现
"""
import logging
from typing import Optional
from app.adapters.image_base import BaseImageAdapter, ImageResult

logger = logging.getLogger(__name__)


class SeedreamImageAdapter(BaseImageAdapter):
    """Seedream 生图平台适配器"""

    def __init__(self, api_key: str, base_url: str, model: str = "seedream-4.0"):
        super().__init__(api_key, base_url, model)

    def generate(self, prompt: str, **kwargs) -> ImageResult:
        """同步生成图片"""
        if not self.is_configured():
            return ImageResult(
                success=False,
                status="failed",
                error_message="Seedream 未配置：请设置 SEEDREAM_API_KEY 和 SEEDREAM_BASE_URL"
            )

        # TODO: 实现 Seedream 同步生图 API 调用
        # 参考实现：
        # import requests
        # response = requests.post(
        #     f"{self.base_url}/images/generations",
        #     headers={"Authorization": f"Bearer {self.api_key}"},
        #     json={
        #         "model": self.model,
        #         "prompt": prompt,
        #         "n": kwargs.get("n", 1),
        #         "size": f"{kwargs.get('width', 1024)}x{kwargs.get('height', 1024)}",
        #     }
        # )
        # result = response.json()
        # return ImageResult(
        #     success=True,
        #     image_urls=[item["url"] for item in result.get("data", [])],
        #     status="succeeded",
        #     width=kwargs.get("width"),
        #     height=kwargs.get("height"),
        #     raw_response=result,
        # )

        logger.warning("Seedream 同步生图 API 调用尚未实现（TODO）")
        return ImageResult(
            success=False,
            status="failed",
            error_message="Seedream 生图功能待实现：API 调用逻辑已预留 TODO"
        )

    def generate_async(self, prompt: str, **kwargs) -> ImageResult:
        """异步提交生图任务"""
        if not self.is_configured():
            return ImageResult(
                success=False,
                status="failed",
                error_message="Seedream 未配置：请设置 SEEDREAM_API_KEY 和 SEEDREAM_BASE_URL"
            )

        # TODO: 实现 Seedream 异步生图任务提交
        # 参考实现：
        # import requests
        # response = requests.post(
        #     f"{self.base_url}/images/generations/async",
        #     headers={"Authorization": f"Bearer {self.api_key}"},
        #     json={"model": self.model, "prompt": prompt, **kwargs}
        # )
        # task_id = response.json().get("id")
        # return ImageResult(success=True, task_id=task_id, status="pending")

        logger.warning("Seedream 异步生图 API 调用尚未实现（TODO）")
        return ImageResult(
            success=False,
            status="failed",
            error_message="Seedream 异步生图功能待实现：API 调用逻辑已预留 TODO"
        )

    def get_status(self, task_id: str) -> ImageResult:
        """查询异步生图任务状态"""
        if not self.is_configured():
            return ImageResult(
                success=False,
                status="failed",
                error_message="Seedream 未配置：请设置 SEEDREAM_API_KEY 和 SEEDREAM_BASE_URL"
            )

        # TODO: 实现 Seedream 异步任务状态查询
        # 参考实现：
        # import requests
        # response = requests.get(
        #     f"{self.base_url}/images/generations/{task_id}",
        #     headers={"Authorization": f"Bearer {self.api_key}"}
        # )
        # result = response.json()
        # return ImageResult(
        #     success=result.get("status") == "succeeded",
        #     task_id=task_id,
        #     status=result.get("status", "unknown"),
        #     image_urls=[item["url"] for item in result.get("data", [])],
        #     error_message=result.get("error"),
        # )

        logger.warning("Seedream 任务状态查询 API 调用尚未实现（TODO）")
        return ImageResult(
            success=False,
            task_id=task_id,
            status="failed",
            error_message="Seedream 任务状态查询待实现：API 调用逻辑已预留 TODO"
        )
