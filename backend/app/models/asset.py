"""数字资产模块数据模型

包含 6 张表：
- AssetSource: 资产源（URL/文件/剪贴板/PubMed）
- AssetDocument: 文档（解析后的全文内容）
- AssetChunk: 分块（父子分块策略，用于语义检索）
- AssetNote: 笔记（用户对文档的手动笔记）
- AssetGenerated: AI生成内容（总结/问答/大纲等）
- PubMedCache: PubMed文献缓存（医学文献专用）
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class AssetSource(Base):
    """资产源 - 用户收藏的原始来源"""
    __tablename__ = "geo_asset_source"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    # 来源类型：url / file / clipboard / manual / pubmed
    source_type = Column(String(20), nullable=False, default="url", index=True)

    # 来源信息
    title = Column(String(500), default="", index=True)
    url = Column(String(2000), default="", index=True)
    source_site = Column(String(200), default="")  # 如: zhihu.com, pubmed.ncbi.nlm.nih.gov
    file_name = Column(String(500), default="")  # 文件名（file类型时用）
    file_path = Column(String(1000), default="")  # 存储路径

    # 处理状态：pending / processing / completed / failed
    status = Column(String(20), default="pending", index=True)
    error_message = Column(Text, default="")

    # 分类标签（用户自定义）
    tags = Column(String(500), default="")
    category = Column(String(50), default="", index=True)  # medicine / business / personal / other

    # 浏览器插件收藏时的额外元数据
    metadata_json = Column(JSON, default=dict)  # {favicon, description, author, ...}

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联
    document = relationship("AssetDocument", back_populates="source", uselist=False)


class AssetDocument(Base):
    """资产文档 - 解析后的文档全文"""
    __tablename__ = "geo_asset_document"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("geo_asset_source.id"), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    # 文档内容
    title = Column(String(500), default="", index=True)
    content = Column(Text, default="")  # Markdown格式全文
    author = Column(String(200), default="")
    publish_date = Column(String(50), default="")  # 原文献发布日期
    summary = Column(Text, default="")  # AI总结

    # 元数据
    word_count = Column(Integer, default=0)
    language = Column(String(20), default="zh")  # zh / en / auto
    tags = Column(String(500), default="")
    category = Column(String(50), default="", index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联
    source = relationship("AssetSource", back_populates="document")
    chunks = relationship("AssetChunk", back_populates="document", cascade="all, delete-orphan")
    notes = relationship("AssetNote", back_populates="document", cascade="all, delete-orphan")
    generated_list = relationship("AssetGenerated", back_populates="document", cascade="all, delete-orphan")


class AssetChunk(Base):
    """资产分块 - 用于语义检索的父子分块"""
    __tablename__ = "geo_asset_chunk"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("geo_asset_document.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    # 分块内容
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, default=0)  # 分块序号
    token_count = Column(Integer, default=0)

    # 父子分块策略
    # parent_id 为空 = 父块（大段，用于展示上下文）
    # parent_id 不为空 = 子块（小块，用于精准检索）
    parent_id = Column(Integer, ForeignKey("geo_asset_chunk.id"), nullable=True, index=True)

    # 向量嵌入（JSON文本数组）
    embedding = Column(Text, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联
    document = relationship("AssetDocument", back_populates="chunks")


class AssetNote(Base):
    """资产笔记 - 用户手动写的笔记/心得"""
    __tablename__ = "geo_asset_note"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("geo_asset_document.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    title = Column(String(500), default="")
    content = Column(Text, default="")  # Markdown格式

    # 笔记类型：personal / clinical / research / teaching
    note_type = Column(String(30), default="personal", index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联
    document = relationship("AssetDocument", back_populates="notes")


class AssetGenerated(Base):
    """AI生成内容 - 系统通过AI生成的总结、问答、大纲等"""
    __tablename__ = "geo_asset_generated"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("geo_asset_document.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    # 生成类型：summary / qa / outline / translation / mindmap
    gen_type = Column(String(30), nullable=False, index=True)
    title = Column(String(500), default="")
    content = Column(Text, default="")

    # AI模型信息
    platform = Column(String(30), default="")  # glm / minimax / deepseek
    model = Column(String(100), default="")
    prompt_template = Column(String(50), default="")  # 使用的prompt模板名称

    # Token用量
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联
    document = relationship("AssetDocument", back_populates="generated_list")


class PubMedCache(Base):
    """PubMed文献缓存 - 医学文献专用"""
    __tablename__ = "geo_pubmed_cache"

    id = Column(Integer, primary_key=True, index=True)
    pmid = Column(String(20), nullable=False, unique=True, index=True)

    # 文献信息
    title = Column(String(1000), default="")
    authors = Column(String(1000), default="")
    journal = Column(String(200), default="")
    publish_date = Column(String(50), default="")
    abstract = Column(Text, default="")
    keywords = Column(String(1000), default="")
    mesh_terms = Column(String(1000), default="")
    doi = Column(String(200), default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AssetChatSession(Base):
    """对话会话 - 与个人知识库对话的会话"""
    __tablename__ = "geo_asset_chat_session"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    # 关联的文档（可选，独立问答时为空）
    document_id = Column(Integer, ForeignKey("geo_asset_document.id"), nullable=True, index=True)

    # 会话信息
    title = Column(String(500), default="新对话")
    platform = Column(String(30), default="glm")  # 当前使用的模型

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联
    messages = relationship("AssetChatMessage", back_populates="session", cascade="all, delete-orphan")


class AssetChatMessage(Base):
    """对话消息"""
    __tablename__ = "geo_asset_chat_message"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("geo_asset_chat_session.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    # 消息内容
    role = Column(String(20), nullable=False)  # user / assistant / system
    content = Column(Text, nullable=False)

    # AI模型信息（assistant消息时记录）
    platform = Column(String(30), default="")
    model = Column(String(100), default="")
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)

    # 引用来源（RAG检索到的文档片段）
    sources = Column(Text, default="")  # JSON数组

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联
    session = relationship("AssetChatSession", back_populates="messages")


class AssetPublished(Base):
    """已发布内容 - 医生从个人知识库发布的公开科普内容（GEO用）"""
    __tablename__ = "geo_asset_published"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    # 来源关联（可选）
    source_document_id = Column(Integer, ForeignKey("geo_asset_document.id"), nullable=True, index=True)

    # 内容信息
    title = Column(String(500), nullable=False, index=True)
    content = Column(Text, nullable=False)  # Markdown格式正文
    summary = Column(Text, default="")  # 摘要
    category = Column(String(50), default="", index=True)
    tags = Column(String(500), default="")

    # 状态：draft / published / archived
    status = Column(String(20), default="draft", index=True)

    # GEO效果追踪（预留）
    view_count = Column(Integer, default=0)  # 浏览量
    citation_count = Column(Integer, default=0)  # 被AI引用次数
    keywords = Column(String(500), default="")  # 目标关键词

    # AI模型信息（发布时用的哪个模型改写的）
    platform = Column(String(30), default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)


class AssetFolder(Base):
    """资产文件夹 - 分组管理"""
    __tablename__ = "geo_asset_folder"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("geo_asset_folder.id"), nullable=True, default=0)  # 最多两级，0=根文件夹
    sort_order = Column(Integer, default=0)
    is_system = Column(Integer, default=0)  # 0=用户自建 1=系统预置（不能删）

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
