"""微信公众号数据统计模型
- WechatAccountStats: 账号每日统计快照
- WechatArticle: 文章基本信息（静态）
- WechatArticleStats: 文章数据快照（发布后1/3/7/30天）
"""
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, Float, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class WechatAccountStats(Base):
    """微信公众号账号每日统计快照"""
    __tablename__ = "geo_wechat_account_stats"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("geo_publish_account.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)
    stat_date = Column(Date, nullable=False, index=True)  # 统计日期

    # 用户数据
    new_users = Column(Integer, default=0)       # 新增关注
    cancel_users = Column(Integer, default=0)    # 取消关注
    net_growth = Column(Integer, default=0)      # 净增
    cumulate_users = Column(Integer, default=0)  # 累计关注用户数

    # 图文数据
    total_articles = Column(Integer, default=0)  # 当天发文数
    total_reads = Column(Integer, default=0)     # 总阅读次数
    total_read_users = Column(Integer, default=0)  # 总阅读人数
    total_shares = Column(Integer, default=0)    # 总分享次数
    total_likes = Column(Integer, default=0)     # 总点赞数
    total_favorites = Column(Integer, default=0) # 总收藏次数
    avg_reads = Column(Float, default=0)         # 平均阅读次数

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_wechat_account_stats_account_date', 'account_id', 'stat_date', unique=True),
    )


class WechatArticle(Base):
    """微信公众号文章基本信息（静态，不随时间变化）"""
    __tablename__ = "geo_wechat_article"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("geo_publish_account.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    title = Column(String(300), default="")       # 文章标题
    article_url = Column(String(500), default="")  # 文章URL
    cover_url = Column(String(500), default="")    # 封面图URL
    author = Column(String(100), default="")        # 作者
    digest = Column(String(500), default="")        # 摘要
    publish_date = Column(Date, nullable=True, index=True)  # 发布日期
    media_id = Column(String(100), default="")      # 微信素材media_id
    content = Column(Text, default="")              # 文章正文（通过本系统发布时同步存储，供AI分析）

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WechatArticleStats(Base):
    """微信公众号文章数据快照（发布后1/3/7/30天各一条）"""
    __tablename__ = "geo_wechat_article_stats"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("geo_wechat_article.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("geo_publish_account.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    snapshot_day = Column(Integer, default=0)  # 快照时间点：1/3/7/30（发布后第N天）
    stat_date = Column(Date, nullable=False, index=True)  # 统计日期

    # 文章数据
    int_page_read_count = Column(Integer, default=0)     # 图文页阅读次数
    int_page_read_user = Column(Integer, default=0)      # 图文页阅读人数
    ori_page_read_user = Column(Integer, default=0)      # 原文页阅读人数
    ori_page_read_count = Column(Integer, default=0)     # 原文页阅读次数
    share_user = Column(Integer, default=0)               # 分享人数
    share_count = Column(Integer, default=0)              # 分享次数
    add_to_fav_user = Column(Integer, default=0)          # 收藏人数
    add_to_fav_count = Column(Integer, default=0)         # 收藏次数
    like_count = Column(Integer, default=0)                # 点赞数
    comment_count = Column(Integer, default=0)             # 评论数

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_wechat_article_stats_article_day', 'article_id', 'snapshot_day', unique=True),
    )
