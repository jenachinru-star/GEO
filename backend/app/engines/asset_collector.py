"""数字资产 - URL采集引擎

负责抓取网页内容并提取正文、标题、作者等元数据。
使用 requests + 正则解析，不依赖额外的HTML解析库（保持轻量）。
"""
import re
import logging
from typing import Dict, Optional
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)


class AssetCollector:
    """URL资产采集器"""

    # 常见User-Agent
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.USER_AGENTS[0],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })

    def collect(self, url: str) -> Dict:
        """抓取URL内容，返回结构化结果

        Returns:
            {
                "title": str,
                "content": str,  # 纯文本正文
                "author": str,
                "publish_date": str,
                "source_site": str,
                "success": bool,
                "error": str,
            }
        """
        try:
            logger.info(f"开始采集URL: {url[:100]}")

            # 验证URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return {"success": False, "error": "无效的URL"}

            # 发起请求
            resp = self.session.get(url, timeout=15, allow_redirects=True)
            resp.raise_for_status()

            # 编码处理
            if not resp.encoding or resp.encoding.lower() == 'iso-8859-1':
                resp.encoding = resp.apparent_encoding or 'utf-8'

            html = resp.text

            # 提取元数据
            title = self._extract_title(html)
            author = self._extract_author(html)
            publish_date = self._extract_publish_date(html)
            content = self._extract_content(html)

            # 来源网站
            source_site = parsed.netloc

            # 检查内容是否太短（JS渲染的网站通常拿不到正文）
            if len(content) < 100:
                logger.warning(f"采集内容过短，可能是JS渲染页面: {len(content)}字符")
                return {
                    "success": False,
                    "error": "该网站需要JavaScript渲染，暂不支持自动采集，请手动粘贴内容",
                    "title": title or "未命名",
                    "content": "",
                    "author": "",
                    "publish_date": "",
                    "source_site": source_site,
                }

            logger.info(f"采集成功: title={title[:50]}, content_len={len(content)}")

            return {
                "success": True,
                "title": title or "未命名",
                "content": content,
                "author": author,
                "publish_date": publish_date,
                "source_site": source_site,
                "error": "",
            }

        except requests.exceptions.Timeout:
            logger.error(f"采集超时: {url}")
            return {"success": False, "error": "请求超时，请检查网络后重试"}
        except requests.exceptions.ConnectionError:
            logger.error(f"连接失败: {url}")
            return {"success": False, "error": "无法连接到目标网站"}
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP错误: {e}")
            return {"success": False, "error": f"HTTP错误: {resp.status_code}"}
        except Exception as e:
            logger.error(f"采集异常: {type(e).__name__}: {e}")
            return {"success": False, "error": f"采集失败: {str(e)[:200]}"}

    def _extract_title(self, html: str) -> str:
        """提取标题"""
        # 尝试 og:title
        m = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
        if m:
            return m.group(1).strip()
        # 尝试 <title>
        m = re.search(r'<title[^>]*>([^<]+)</title>', html, re.I)
        if m:
            return m.group(1).strip()
        return ""

    def _extract_author(self, html: str) -> str:
        """提取作者"""
        # 尝试 meta author
        m = re.search(r'<meta[^>]*name=["\']author["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
        if m:
            return m.group(1).strip()
        # 尝试 article:author
        m = re.search(r'<meta[^>]*property=["\']article:author["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
        if m:
            return m.group(1).strip()
        return ""

    def _extract_publish_date(self, html: str) -> str:
        """提取发布日期"""
        # 尝试 article:published_time
        m = re.search(r'<meta[^>]*property=["\']article:published_time["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
        if m:
            return m.group(1).strip()[:10]
        # 尝试 datePublished
        m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
        if m:
            return m.group(1).strip()[:10]
        return ""

    def _extract_content(self, html: str) -> str:
        """提取正文内容（简化版，去除HTML标签和脚本）"""
        # 移除 script, style, nav, footer 等非正文标签
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.I | re.S)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.I | re.S)
        html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.I | re.S)
        html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.I | re.S)
        html = re.sub(r'<header[^>]*>.*?</header>', '', html, flags=re.I | re.S)
        html = re.sub(r'<!--.*?-->', '', html, flags=re.S)

        # 尝试提取 article 标签内的内容
        article_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.I | re.S)
        if article_match:
            content = article_match.group(1)
        else:
            # 尝试 main 标签
            main_match = re.search(r'<main[^>]*>(.*?)</main>', html, re.I | re.S)
            if main_match:
                content = main_match.group(1)
            else:
                content = html

        # 转换常见块级标签为换行
        content = re.sub(r'<br\s*/?>', '\n', content, flags=re.I)
        content = re.sub(r'</(p|div|h[1-6]|li)>', '\n', content, flags=re.I)

        # 移除所有剩余HTML标签
        content = re.sub(r'<[^>]+>', '', content)

        # HTML实体解码（简单处理）
        content = content.replace('&nbsp;', ' ')
        content = content.replace('&amp;', '&')
        content = content.replace('&lt;', '<')
        content = content.replace('&gt;', '>')
        content = content.replace('&quot;', '"')
        content = content.replace('&#39;', "'")

        # 清理多余空行和空格
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        content = content.strip()

        return content


# 全局实例
asset_collector = AssetCollector()
