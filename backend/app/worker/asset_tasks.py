"""数字资产相关任务的处理函数

任务类型：
- asset_url_collect: URL网页采集
- asset_file_parse: 文件解析

两个任务完成后都会自动执行：分块 + 向量化 + AI自动打标签
"""
import json
import logging
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.models.asset import AssetSource, AssetDocument, AssetChunk
from app.engines.asset_collector import asset_collector
from app.engines.asset_parser import asset_parser
from app.engines.asset_chunker import asset_chunker
from app.engines.asset_embedder import asset_embedder
from app.adapters import adapter_factory
from app.worker.task_registry import register_handler, ProgressCallback

logger = logging.getLogger(__name__)


def _process_document_chunks(db: Session, doc: AssetDocument, on_progress: ProgressCallback = None):
    """对文档执行分块和向量化

    在文档解析完成后调用，自动生成父子块并计算向量
    """
    if not doc.content or len(doc.content) < 100:
        logger.info(f"文档内容太短，跳过分块: doc_id={doc.id}")
        return

    if on_progress:
        on_progress(4, 5, "正在分块...")

    # 分块
    chunks = asset_chunker.chunk_document(doc.content, doc.title)
    if not chunks:
        logger.warning(f"分块结果为空: doc_id={doc.id}")
        return

    if on_progress:
        on_progress(5, 5, f"正在向量化（{len(chunks)}块）...")

    # 逐块生成向量并保存
    for i, (chunk_text, parent_idx) in enumerate(chunks):
        # 生成向量
        vec = asset_embedder.embed_text(chunk_text)
        vec_json = asset_embedder.vector_to_json(vec)

        # 确定parent_id
        parent_id = None
        if parent_idx >= 0:
            # 子块：找对应的父块（父块是同文档中chunk_index等于parent_idx的块）
            parent_chunk = db.query(AssetChunk).filter(
                AssetChunk.document_id == doc.id,
                AssetChunk.chunk_index == parent_idx,
                AssetChunk.parent_id.is_(None),
            ).first()
            if parent_chunk:
                parent_id = parent_chunk.id

        chunk = AssetChunk(
            document_id=doc.id,
            user_id=doc.user_id,
            content=chunk_text,
            chunk_index=i,
            token_count=len(chunk_text) // 2,  # 粗略估算
            parent_id=parent_id,
            embedding=vec_json,
        )
        db.add(chunk)

    db.commit()
    logger.info(f"分块向量化完成: doc_id={doc.id}, chunks={len(chunks)}")


def _auto_tag_document(db: Session, source: AssetSource, doc: AssetDocument):
    """AI自动为文档生成标签和分类

    使用GLM-flash轻量模型，根据标题和前500字内容生成3-5个标签和分类
    """
    # 如果用户已经手动填了标签或分类，就不自动覆盖
    if source.tags or source.category:
        logger.info(f"已有手动标签，跳过自动打标签: source_id={source.id}")
        return

    try:
        adapter = adapter_factory.get_adapter("glm")
        if not adapter:
            logger.info("GLM适配器未配置，跳过自动打标签")
            return

        # 取前500字作为参考
        preview = (doc.content or "")[:500]

        prompt = f"""请为这篇文章生成标签和分类。

文章标题：{doc.title}
内容预览：{preview}

请按以下JSON格式返回：
{{
  "tags": ["标签1", "标签2", "标签3"],
  "category": "medicine/business/personal/other 其中之一"
}}

要求：
- 标签3-5个，简洁精准，中文
- category四选一：medicine（医学）、business（行业资讯）、personal（个人笔记）、other（其他）
- 只返回JSON，不要其他内容"""

        result = adapter.query(
            prompt,
            system_prompt="你是一个文章分类和标签生成助手，只返回JSON格式。",
            usage_ctx={"task_type": "asset_auto_tag", "source": "worker"}
        )

        if result.success and result.answer:
            # 解析JSON
            answer = result.answer.strip()
            # 去掉可能的markdown代码块标记
            if answer.startswith("```"):
                answer = answer.split("```")[1]
                if answer.startswith("json"):
                    answer = answer[4:]
                answer = answer.strip()

            tag_data = json.loads(answer)
            tags = tag_data.get("tags", [])
            category = tag_data.get("category", "other")

            # 更新source
            source.tags = ",".join(tags[:5])
            if not source.category:
                source.category = category

            # 同步到document
            doc.tags = source.tags
            doc.category = source.category

            db.commit()
            logger.info(f"自动打标签完成: source_id={source.id}, tags={source.tags}, category={source.category}")

    except Exception as e:
        logger.warning(f"自动打标签失败（不影响主流程）: {e}")


def handle_asset_url_collect(db: Session, task: AsyncTask, on_progress: ProgressCallback = None) -> dict:
    """处理 URL 网页采集任务"""
    payload = json.loads(task.payload_json or "{}")
    source_id = payload.get("source_id")

    if not source_id:
        raise ValueError("payload 中缺少 source_id")

    if on_progress:
        on_progress(1, 5, "开始采集网页内容")

    source = db.query(AssetSource).filter(AssetSource.id == source_id).first()
    if not source:
        raise ValueError(f"资产源 #{source_id} 不存在")

    source.status = "processing"
    db.commit()

    try:
        if on_progress:
            on_progress(2, 5, "正在抓取网页...")

        result = asset_collector.collect(source.url)

        if not result["success"]:
            source.status = "failed"
            source.error_message = result["error"]
            db.commit()
            raise ValueError(f"采集失败: {result['error']}")

        if on_progress:
            on_progress(3, 5, "保存解析结果")

        doc = AssetDocument(
            source_id=source.id,
            user_id=source.user_id,
            title=result["title"],
            content=result["content"],
            author=result["author"],
            publish_date=result["publish_date"],
            word_count=len(result["content"]),
            source_site=result.get("source_site", source.source_site),
        )
        db.add(doc)

        source.status = "processing"  # 还需要分块向量化
        if not source.title:
            source.title = result["title"]
        source.source_site = result.get("source_site", source.source_site)
        db.commit()
        db.refresh(doc)

        # 分块和向量化
        _process_document_chunks(db, doc, on_progress)

        # AI自动打标签
        _auto_tag_document(db, source, doc)

        source.status = "completed"
        db.commit()

        logger.info(f"URL采集+向量化完成: source_id={source_id}, doc_id={doc.id}")
        return {"source_id": source_id, "document_id": doc.id, "word_count": len(result["content"])}

    except Exception as e:
        source.status = "failed"
        source.error_message = str(e)[:500]
        db.commit()
        raise


def handle_asset_file_parse(db: Session, task: AsyncTask, on_progress: ProgressCallback = None) -> dict:
    """处理文件解析任务"""
    payload = json.loads(task.payload_json or "{}")
    source_id = payload.get("source_id")
    file_path = payload.get("file_path")
    file_name = payload.get("file_name", "")

    if not source_id:
        raise ValueError("payload 中缺少 source_id")
    if not file_path:
        raise ValueError("payload 中缺少 file_path")

    if on_progress:
        on_progress(1, 5, "开始解析文件")

    source = db.query(AssetSource).filter(AssetSource.id == source_id).first()
    if not source:
        raise ValueError(f"资产源 #{source_id} 不存在")

    source.status = "processing"
    db.commit()

    try:
        if on_progress:
            on_progress(2, 5, "正在提取文本...")

        result = asset_parser.parse_file(file_path, file_name)

        if not result["success"]:
            source.status = "failed"
            source.error_message = result["error"]
            db.commit()
            raise ValueError(f"解析失败: {result['error']}")

        if on_progress:
            on_progress(3, 5, "保存解析结果")

        doc = AssetDocument(
            source_id=source.id,
            user_id=source.user_id,
            title=result["title"],
            content=result["content"],
            word_count=len(result["content"]),
        )
        db.add(doc)

        source.status = "processing"
        if not source.title:
            source.title = result["title"]
        db.commit()
        db.refresh(doc)

        # 分块和向量化
        _process_document_chunks(db, doc, on_progress)

        # AI自动打标签
        _auto_tag_document(db, source, doc)

        source.status = "completed"
        db.commit()

        logger.info(f"文件解析+向量化完成: source_id={source_id}, doc_id={doc.id}")
        return {"source_id": source_id, "document_id": doc.id, "word_count": len(result["content"])}

    except Exception as e:
        source.status = "failed"
        source.error_message = str(e)[:500]
        db.commit()
        raise


# 注册任务处理函数
register_handler("asset_url_collect", handle_asset_url_collect)
register_handler("asset_file_parse", handle_asset_file_parse)
