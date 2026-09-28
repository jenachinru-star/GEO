"""对标账号模型（内容运营模块，独立于GEO监测的Competitor模型）
- BenchmarkAccount: 对标公众号账号（手动输入数据，留好接口后续接入第三方）
- BenchmarkArticle: 对标账号的文章（手动输入）
"""
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class BenchmarkAccount(Base):
    """对标公众号账号"""
    __tablename__ = "geo_benchmark_account"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    # 账号基本信息
    account_name = Column(String(200), nullable=False)  # 公众号名称
    wechat_id = Column(String(100), default="")          # 微信号
    avatar_url = Column(String(500), default="")          # 头像URL
    description = Column(Text, default="")                 # 账号简介
    industry = Column(String(100), default="")             # 行业领域

    # 手动输入的关键数据（后续可由第三方数据平台自动更新）
    followers = Column(Integer, default=0)          # 粉丝数
    avg_reads = Column(Integer, default=0)           # 平均阅读量
    avg_likes = Column(Integer, default=0)            # 平均点赞数
    avg_shares = Column(Integer, default=0)           # 平均分享数
    weekly_posts = Column(Integer, default=0)         # 每周发文数

    # 数据来源标记（manual=手动输入，后续可改为 newrank/xigu 等第三方）
    data_source = Column(String(50), default="manual")
    last_updated = Column(DateTime(timezone=True), nullable=True)  # 数据最后更新时间

    note = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class BenchmarkArticle(Base):
    """对标账号的文章（手动输入）"""
    __tablename__ = "geo_benchmark_article"

    id = Column(Integer, primary_key=True, index=True)
    benchmark_id = Column(Integer, ForeignKey("geo_benchmark_account.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    title = Column(String(300), default="")       # 文章标题
    article_url = Column(String(500), default="")  # 文章URL
    publish_date = Column(Date, nullable=True, index=True)  # 发布日期

    # 手动输入的文章数据
    reads = Column(Integer, default=0)       # 阅读量
    likes = Column(Integer, default=0)        # 点赞数
    shares = Column(Integer, default=0)       # 分享数
    favorites = Column(Integer, default=0)    # 收藏数

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_benchmark_article_benchmark_date', 'benchmark_id', 'publish_date'),
    )
