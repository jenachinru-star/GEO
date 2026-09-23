"""创建微信公众号数据统计表
运行方式：cd backend && C:\\Users\\jenac\\miniconda3\\python.exe -m migrations.add_wechat_stats_tables
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base
from app.models.wechat_stats import WechatAccountStats, WechatArticle, WechatArticleStats

def upgrade():
    print("创建微信公众号数据统计表...")
    # 创建所有表（已存在的表不会重复创建）
    Base.metadata.create_all(bind=engine, tables=[
        WechatAccountStats.__table__,
        WechatArticle.__table__,
        WechatArticleStats.__table__,
    ])
    print("✅ 表创建完成")
    print("  - geo_wechat_account_stats (账号每日统计)")
    print("  - geo_wechat_article (文章基本信息)")
    print("  - geo_wechat_article_stats (文章数据快照)")

if __name__ == "__main__":
    upgrade()
