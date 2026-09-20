"""PubMed文献抓取引擎

使用NCBI E-utilities API（免费，无需Key）
文档：https://www.ncbi.nlm.nih.gov/books/NBK25500/
"""
import logging
import requests
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

PUBMED_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedFetcher:
    """PubMed文献抓取器"""

    def __init__(self):
        self.base_url = PUBMED_EUTILS_BASE
        self.timeout = 30

    def search_pubmed(self, query: str, max_results: int = 10) -> Dict:
        """搜索PubMed，返回PMID列表和摘要信息

        Args:
            query: 搜索关键词
            max_results: 最多返回结果数

        Returns:
            {
                "count": 总数,
                "papers": [{pmid, title, journal, year, authors}],
            }
        """
        try:
            # 第一步：esearch 搜索，获取PMID列表
            search_url = f"{self.base_url}/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "sort": "relevance",
            }
            resp = requests.get(search_url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            count = data.get("esearchresult", {}).get("count", 0)
            pmids = data.get("esearchresult", {}).get("idlist", [])

            if not pmids:
                return {"count": 0, "papers": []}

            # 第二步：efetch 获取详细信息（批量）
            papers = self._fetch_papers_by_pmids(pmids)

            return {"count": int(count), "papers": papers}

        except Exception as e:
            logger.error(f"PubMed搜索失败: {e}")
            raise

    def fetch_by_pmid(self, pmid: str) -> Dict:
        """根据PMID获取单篇文献详情

        Returns:
            {
                "pmid": "12345678",
                "title": "...",
                "abstract": "...",
                "authors": ["作者1", "作者2"],
                "journal": "...",
                "publish_date": "...",
                "doi": "...",
                "mesh_terms": [...],
                "keywords": [...],
            }
        """
        papers = self._fetch_papers_by_pmids([pmid])
        if not papers:
            raise ValueError(f"PMID {pmid} 未找到")
        return papers[0]

    def _fetch_papers_by_pmids(self, pmids: List[str]) -> List[Dict]:
        """根据PMID列表批量获取文献详情"""
        if not pmids:
            return []

        try:
            fetch_url = f"{self.base_url}/efetch.fcgi"
            params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "xml",
            }
            resp = requests.get(fetch_url, params=params, timeout=self.timeout)
            resp.raise_for_status()

            # 解析XML
            root = ET.fromstring(resp.content)
            papers = []

            for article in root.findall(".//PubmedArticle"):
                paper = self._parse_article_xml(article)
                if paper:
                    papers.append(paper)

            return papers

        except Exception as e:
            logger.error(f"PubMed批量获取失败: {e}")
            raise

    def _parse_article_xml(self, article_elem) -> Optional[Dict]:
        """解析单篇文献XML"""
        try:
            medline = article_elem.find(".//MedlineCitation")
            if medline is None:
                return None

            pmid_elem = medline.find("PMID")
            pmid = pmid_elem.text if pmid_elem is not None else ""

            # 标题
            title_elem = medline.find(".//ArticleTitle")
            title = "".join(title_elem.itertext()) if title_elem is not None else ""

            # 摘要
            abstract_parts = []
            for abstract_text in medline.findall(".//AbstractText"):
                label = abstract_text.get("Label")
                text = "".join(abstract_text.itertext())
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
            abstract = "\n\n".join(abstract_parts)

            # 作者
            authors = []
            for author in medline.findall(".//Author"):
                last_name = author.find("LastName")
                fore_name = author.find("ForeName")
                if last_name is not None and fore_name is not None:
                    authors.append(f"{fore_name.text} {last_name.text}")
                elif last_name is not None:
                    authors.append(last_name.text)

            # 期刊
            journal_elem = medline.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None else ""

            # 发表日期
            year_elem = medline.find(".//JournalIssue/PubDate/Year")
            month_elem = medline.find(".//JournalIssue/PubDate/Month")
            day_elem = medline.find(".//JournalIssue/PubDate/Day")
            publish_date_parts = []
            if year_elem is not None:
                publish_date_parts.append(year_elem.text)
            if month_elem is not None:
                publish_date_parts.append(month_elem.text)
            if day_elem is not None:
                publish_date_parts.append(day_elem.text)
            publish_date = " ".join(publish_date_parts)

            # DOI
            doi = ""
            for article_id in medline.findall(".//ArticleId"):
                if article_id.get("IdType") == "doi":
                    doi = article_id.text or ""
                    break

            # Mesh主题词
            mesh_terms = []
            for mesh in medline.findall(".//MeshHeading/DescriptorName"):
                if mesh.text:
                    mesh_terms.append(mesh.text)

            # 关键词
            keywords = []
            for kw in medline.findall(".//Keyword"):
                if kw.text:
                    keywords.append(kw.text)

            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "journal": journal,
                "publish_date": publish_date,
                "doi": doi,
                "mesh_terms": mesh_terms,
                "keywords": keywords,
            }

        except Exception as e:
            logger.warning(f"解析文献XML失败: {e}")
            return None


# 全局单例
pubmed_fetcher = PubMedFetcher()
