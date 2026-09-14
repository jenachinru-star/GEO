from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class QueryResult:
    """平台查询结果"""
    platform_code: str
    answer: str
    success: bool
    error: Optional[str] = None
    raw_response: Optional[dict] = None


class BaseAdapter(ABC):
    """平台适配器基类"""

    def __init__(self, api_key: str, base_url: str, model: str,
                 temperature: float = 0.3, max_tokens: int = 2000):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    def query(self, question: str, system_prompt: Optional[str] = None) -> QueryResult:
        """向AI平台发起提问，返回回答
        Args:
            question: 用户问题
            system_prompt: 可选的系统提示词
        """
        pass

    @abstractmethod
    def get_platform_code(self) -> str:
        """返回平台标识"""
        pass
