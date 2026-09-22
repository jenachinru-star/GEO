"""数字资产 - PubMed文献导入 API

功能：
- PMID导入文献
- 关键词搜索PubMed
- 批量导入
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_user_id
from app.models.asset import AssetSource, AssetDocument, PubMedCache
from app.engines.pubmed_fetcher import pubmed_fetcher
from app.engines.asset_embedder import asset_embedder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/asset/pubmed", tags=["数字资产-PubMed"])


# ============ 请求体模型 ============

class PMIDImportRequest(BaseModel):
    pmid: str
    category: str = "medicine"
    tags: str = ""


class PubMedSearchRequest(BaseModel):
    query: str
    max_results: int = 10


class BatchImportRequest(BaseModel):
    pmids: List[str]
    category: str = "medicine"


# ============ 搜索PubMed ============

@router.post("/search", summary="搜索PubMed文献")
def search_pubmed(
    req: PubMedSearchRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """搜索PubMed，返回文献列表"""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="搜索关键词不能为空")

    try:
        result = pubmed_fetcher.search_pubmed(req.query, req.max_results)

        # 标记哪些已经导入过
        pmids = [p["pmid"] for p in result["papers"]]
        existing_query = db.query(AssetSource).filter(
            AssetSource.user_id == user_id,
            AssetSource.source_type == "pubmed",
        )
        if pmids:
            existing_query = existing_query.filter(
                or_(*[AssetSource.url.contains(pmid) for pmid in pmids])
            )
        existing = existing_query.all()
        existing_pmids = set()
        for s in existing:
            # 从url中提取pmid
            if s.url and "pubmed" in s.url:
                existing_pmids.add(s.url.split("/")[-1].rstrip("/"))

        for paper in result["papers"]:
            paper["imported"] = paper["pmid"] in existing_pmids

        return {"code": 0, "message": "success", "data": result}

    except Exception as e:
        logger.error(f"PubMed搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


# ============ 导入单篇文献 ============

@router.post("/import", summary="导入单篇PubMed文献")
def import_pubmed(
    req: PMIDImportRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """根据PMID导入单篇文献到个人知识库"""
    pmid = req.pmid.strip()
    if not pmid:
        raise HTTPException(status_code=400, detail="PMID不能为空")

    # 检查是否已导入
    existing = db.query(AssetSource).filter(
        AssetSource.user_id == user_id,
        AssetSource.source_type == "pubmed",
        AssetSource.url.like(f"%{pmid}%"),
    ).first()
    if existing:
        return {"code": 0, "message": "该文献已导入", "data": {"source_id": existing.id, "already_exists": True}}

    # 检查缓存
    cached = db.query(PubMedCache).filter(PubMedCache.pmid == pmid).first()
    if cached:
        paper = {
            "pmid": cached.pmid,
            "title": cached.title,
            "abstract": cached.abstract,
            "authors": cached.authors,
            "journal": cached.journal,
            "publish_date": cached.publish_date,
            "doi": cached.doi,
            "mesh_terms": cached.mesh_terms,
            "keywords": cached.keywords,
        }
    else:
        # 从PubMed抓取
        try:
            paper = pubmed_fetcher.fetch_by_pmid(pmid)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"抓取PubMed失败: {str(e)}")

        # 存入缓存
        cache = PubMedCache(
            pmid=pmid,
            title=paper["title"],
            authors=", ".join(paper["authors"]),
            journal=paper["journal"],
            publish_date=paper["publish_date"],
            abstract=paper["abstract"],
            keywords=", ".join(paper["keywords"]),
            mesh_terms=", ".join(paper["mesh_terms"]),
            doi=paper["doi"],
        )
        db.add(cache)

    # 创建资产源
    source = AssetSource(
        user_id=user_id,
        source_type="pubmed",
        title=paper["title"],
        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        source_site="pubmed.ncbi.nlm.nih.gov",
        status="completed",
        category=req.category,
        tags=req.tags or ",".join(paper["keywords"][:5]),
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    # 创建文档
    content = f"""# {paper['title']}

**作者：** {', '.join(paper['authors'])}

**期刊：** {paper['journal']}

**发表日期：** {paper['publish_date']}

**PMID：** {paper['pmid']}

**DOI：** {paper['doi']}

---

## 摘要

{paper['abstract']}

---

**Mesh主题词：** {', '.join(paper['mesh_terms'])}

**关键词：** {', '.join(paper['keywords'])}
"""

    doc = AssetDocument(
        source_id=source.id,
        is_current=True,
        version=1,
        user_id=user_id,
        title=paper["title"],
        content=content,
        author=", ".join(paper["authors"][:3]) + (" et al." if len(paper["authors"]) > 3 else ""),
        publish_date=paper["publish_date"],
        word_count=len(paper["abstract"]),
        tags=req.tags or ",".join(paper["keywords"][:5]),
        category=req.category,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 异步分块向量化（这里先同步做，简单点）
    try:
        from app.engines.asset_chunker import asset_chunker
        from app.engines.asset_embedder import asset_embedder

        chunks = asset_chunker.chunk_document(doc.content, doc.title)
        if chunks:
            for i, (chunk_text, parent_idx) in enumerate(chunks):
                vec = asset_embedder.embed_text(chunk_text)
                vec_json = asset_embedder.vector_to_json(vec)
                from app.models.asset import AssetChunk
                chunk = AssetChunk(
                    document_id=doc.id,
                    user_id=user_id,
                    content=chunk_text,
                    chunk_index=i,
                    token_count=len(chunk_text) // 2,
                    embedding=vec_json,
                )
                db.add(chunk)
            db.commit()
    except Exception as e:
        logger.warning(f"PubMed文献分块向量化失败: {e}")

    return {
        "code": 0,
        "message": "导入成功",
        "data": {
            "source_id": source.id,
            "document_id": doc.id,
            "title": paper["title"],
        }
    }


# ============ 批量导入 ============

@router.post("/batch-import", summary="批量导入PubMed文献")
def batch_import(
    req: BatchImportRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """批量导入多个PMID"""
    if not req.pmids:
        raise HTTPException(status_code=400, detail="PMID列表不能为空")

    if len(req.pmids) > 20:
        raise HTTPException(status_code=400, detail="一次最多导入20篇")

    results = []
    success_count = 0
    fail_count = 0

    for pmid in req.pmids:
        try:
            # 检查是否已导入
            existing = db.query(AssetSource).filter(
                AssetSource.user_id == user_id,
                AssetSource.source_type == "pubmed",
                AssetSource.url.like(f"%{pmid}%"),
            ).first()
            if existing:
                results.append({"pmid": pmid, "status": "already_exists"})
                continue

            # 抓取
            paper = pubmed_fetcher.fetch_by_pmid(pmid)

            # 创建资产
            source = AssetSource(
                user_id=user_id,
                source_type="pubmed",
                title=paper["title"],
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                source_site="pubmed.ncbi.nlm.nih.gov",
                status="completed",
                category=req.category,
            )
            db.add(source)
            db.commit()
            db.refresh(source)

            content = f"# {paper['title']}\n\n**作者：** {', '.join(paper['authors'])}\n\n**期刊：** {paper['journal']}\n\n**摘要：**\n\n{paper['abstract']}"
            doc = AssetDocument(
                source_id=source.id,
                user_id=user_id,
                title=paper["title"],
                content=content,
                author=", ".join(paper["authors"][:3]),
                publish_date=paper["publish_date"],
            )
            db.add(doc)
            db.commit()

            results.append({"pmid": pmid, "status": "success", "title": paper["title"]})
            success_count += 1

        except Exception as e:
            results.append({"pmid": pmid, "status": "failed", "error": str(e)})
            fail_count += 1

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": len(req.pmids),
            "success": success_count,
            "failed": fail_count,
            "results": results,
        }
    }
