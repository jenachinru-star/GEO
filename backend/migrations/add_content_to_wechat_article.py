# -*- coding: utf-8 -*-
"""WechatArticle表增加content字段
运行方式：cd backend && C:\\Users\\jenac\\miniconda3\\python.exe -m migrations.add_content_to_wechat_article
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from sqlalchemy import text


def upgrade():
    print("为 geo_wechat_article 表增加 content 字段...")
    with engine.connect() as conn:
        # 检查字段是否已存在
        result = conn.execute(text("PRAGMA table_info(geo_wechat_article)"))
        columns = [row[1] for row in result.fetchall()]
        if 'content' in columns:
            print("⚠️ content 字段已存在，跳过")
            return
        conn.execute(text("ALTER TABLE geo_wechat_article ADD COLUMN content TEXT DEFAULT ''"))
        conn.commit()
    print("✅ content 字段添加完成")


if __name__ == "__main__":
    upgrade()
