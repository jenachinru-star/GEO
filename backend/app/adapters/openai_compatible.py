"""通用OpenAI兼容平台适配器
所有OpenAI兼容格式的平台（GLM、MiniMax、豆包、通义等）都继承这个类，
只需要指定platform_code，不需要重复写query和_extract_answer逻辑。
"""
from openai import OpenAI
from typing import Optional
from app.adapters.base import BaseAdapter, QueryResult
import traceback
import logging

logger = logging.getLogger(__name__)


class OpenAICompatibleAdapter(BaseAdapter):
    """OpenAI兼容格式通用适配器"""

    platform_code: str = "generic"  # 子类覆盖

    def __init__(self, api_key: str, base_url: str, model: str,
                 temperature: float = 0.3, max_tokens: int = 2000):
        super().__init__(api_key, base_url, model, temperature, max_tokens)
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=120
        )

    def _extract_answer(self, response) -> str:
        """从响应中提取回答文本，处理各种情况"""
        try:
            if not response or not response.choices or len(response.choices) == 0:
                logger.warning(f"{self.platform_code}响应无choices: {response}")
                return ""

            message = response.choices[0].message

            # 优先取content
            content = message.content
            if content and content.strip():
                return content.strip()

            # 如果content为空，检查是否有reasoning_content（思考模型）
            reasoning = getattr(message, 'reasoning_content', None)
            if reasoning and reasoning.strip():
                logger.info(f"{self.platform_code}使用reasoning_content作为回答")
                return reasoning.strip()

            if hasattr(response, 'model_dump'):
                raw = response.model_dump()
                logger.warning(f"{self.platform_code}响应结构: {str(raw)[:500]}")

            logger.warning(f"{self.platform_code}回答为空，message: {message}")
            return ""

        except Exception as e:
            logger.error(f"提取{self.platform_code}回答失败: {e}")
            return ""

    def query(self, question: str, system_prompt: Optional[str] = None) -> QueryResult:
        try:
            logger.info(f"{self.platform_code}请求: model={self.model}, temp={self.temperature}, question={question[:50]}")

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": question})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            answer = self._extract_answer(response)

            if answer:
                logger.info(f"{self.platform_code}回答长度: {len(answer)}")
                return QueryResult(
                    platform_code=self.platform_code,
                    answer=answer,
                    success=True,
                    raw_response=response.model_dump() if hasattr(response, 'model_dump') else None
                )
            else:
                return QueryResult(
                    platform_code=self.platform_code,
                    answer="",
                    success=False,
                    error="模型返回空回答（可能是思考模型或内容审核）"
                )

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"{self.platform_code}调用异常: {error_msg[:500]}")
            return QueryResult(
                platform_code=self.platform_code,
                answer="",
                success=False,
                error=error_msg
            )

    def get_platform_code(self) -> str:
        return self.platform_code

    def query_stream(self, question: str, system_prompt: Optional[str] = None):
        """流式查询，yield每个token片段

        返回生成器，yield (text_chunk, is_finished, usage_info)
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": question})

            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
                stream_options={"include_usage": True}
            )

            full_answer = ""
            for chunk in stream:
                if not chunk.choices:
                    # 可能是usage chunk
                    if hasattr(chunk, 'usage') and chunk.usage:
                        yield ("", False, {
                            "tokens_input": chunk.usage.prompt_tokens or 0,
                            "tokens_output": chunk.usage.completion_tokens or 0,
                        })
                    continue

                delta = chunk.choices[0].delta
                content = getattr(delta, 'content', None)

                if content:
                    full_answer += content
                    yield (content, False, None)

            # 最后一个chunk：完成标记
            yield ("", True, None)

        except Exception as e:
            logger.error(f"{self.platform_code}流式调用异常: {e}")
            yield (f"[流式错误: {str(e)}]", True, None)
