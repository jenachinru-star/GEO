"""只提取可公开审计的响应字段，不持久化密钥或请求头。"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


SOURCE_KEYS = ("web_search", "sources", "citations", "search_results")


def safe_error_code(exc: Exception) -> str:
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    if "timeout" in name or "timeout" in message:
        return "timeout"
    if "rate" in message or "429" in message:
        return "rate_limited"
    if "401" in message or "403" in message or "auth" in message:
        return "auth_error"
    if "connection" in name or "connection" in message:
        return "connection_error"
    return "provider_error"


def safe_error_message(exc: Exception) -> str:
    # 不保存 traceback、请求头或可能出现的认证信息。
    message = " ".join(str(exc).split())
    return message[:500]


def _candidate_url(value: dict[str, Any]) -> str | None:
    for key in ("url", "link", "href"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.startswith(("http://", "https://")):
            return candidate
    return None


def _normalize_source(value: Any) -> dict[str, Any] | None:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return {"url": value, "domain": urlparse(value).hostname or ""}
    if not isinstance(value, dict):
        return None
    url = _candidate_url(value)
    if not url:
        return None
    return {
        "url": url,
        "domain": urlparse(url).hostname or "",
        "title": str(value.get("title") or "")[:500],
        "media": str(value.get("media") or value.get("site_name") or "")[:200],
        "publish_date": str(value.get("publish_date") or "")[:100],
        "content": str(value.get("content") or value.get("snippet") or "")[:2000],
    }


def extract_sources(raw: dict[str, Any]) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    seen: set[str] = set()

    containers: list[Any] = []
    for key in SOURCE_KEYS:
        if key in raw:
            containers.append(raw[key])

    message = (((raw.get("choices") or [{}])[0] or {}).get("message") or {})
    for key in SOURCE_KEYS:
        if key in message:
            containers.append(message[key])

    for container in containers:
        values = container if isinstance(container, list) else [container]
        for value in values:
            source = _normalize_source(value)
            if source and source["url"] not in seen:
                seen.add(source["url"])
                collected.append(source)
    return collected
