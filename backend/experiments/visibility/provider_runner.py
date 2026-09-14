"""GLM 影子调用器；不使用正式 Collector，不写正式数据库。"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI

from app.config import settings
from experiments.visibility.normalize import extract_sources, safe_error_code, safe_error_message
from experiments.visibility.schemas import RenderedQuestion, ShadowObservation


class GLMShadowRunner:
    provider = "glm"

    def __init__(self) -> None:
        if not settings.GLM_API_KEY or not settings.GLM_BASE_URL:
            raise RuntimeError("GLM_API_KEY/GLM_BASE_URL 未配置")
        self.model = settings.GLM_MODEL
        self.client = OpenAI(
            api_key=settings.GLM_API_KEY,
            base_url=settings.GLM_BASE_URL,
            timeout=120,
        )

    def run(
        self,
        experiment_id: str,
        question: RenderedQuestion,
        mode: str,
        sample_index: int,
    ) -> ShadowObservation:
        started = time.perf_counter()
        collected_at = datetime.now(timezone.utc).isoformat()
        try:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": [{"role": "user", "content": question.text}],
                "temperature": settings.MONITOR_TEMPERATURE,
                "max_tokens": settings.MONITOR_MAX_TOKENS,
            }
            if mode == "grounded_search":
                kwargs["extra_body"] = {
                    "tools": [{
                        "type": "web_search",
                        "web_search": {
                            "enable": True,
                            "search_result": True,
                            "count": 5,
                            "search_recency_filter": "noLimit",
                            "content_size": "medium",
                        },
                    }]
                }

            response = self.client.chat.completions.create(**kwargs)
            raw = response.model_dump() if hasattr(response, "model_dump") else {}
            message = response.choices[0].message if response.choices else None
            answer = (message.content or "").strip() if message else ""
            sources = extract_sources(raw)
            status = "succeeded" if answer else "failed"
            error_code = None if answer else "empty_response"
            return ShadowObservation(
                experiment_id=experiment_id,
                question_id=question.id,
                intent_type=question.intent_type,
                branded=question.branded,
                question_text=question.text,
                purpose=question.purpose,
                provider=self.provider,
                configured_model=self.model,
                response_model=raw.get("model"),
                mode=mode,
                sample_index=sample_index,
                status=status,
                answer=answer,
                sources=sources,
                request_id=raw.get("request_id") or raw.get("id"),
                latency_ms=round((time.perf_counter() - started) * 1000),
                usage=raw.get("usage") or {},
                error_code=error_code,
                error_message="模型返回空正文" if not answer else None,
                collected_at=collected_at,
            )
        except Exception as exc:
            return ShadowObservation(
                experiment_id=experiment_id,
                question_id=question.id,
                intent_type=question.intent_type,
                branded=question.branded,
                question_text=question.text,
                purpose=question.purpose,
                provider=self.provider,
                configured_model=self.model,
                response_model=None,
                mode=mode,
                sample_index=sample_index,
                status="failed",
                latency_ms=round((time.perf_counter() - started) * 1000),
                error_code=safe_error_code(exc),
                error_message=safe_error_message(exc),
                collected_at=collected_at,
            )
