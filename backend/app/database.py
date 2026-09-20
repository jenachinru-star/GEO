from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
import os

# 确保data目录存在
os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"), exist_ok=True)

# SQLite需要加check_same_thread=False
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """获取数据库会话依赖"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表"""
    from app.models import platform, question, monitor, content, knowledge, competitor, user, doctor, semantic, article, subscription, distribution
    from app.models import asset  # 数字资产模块
    Base.metadata.create_all(bind=engine)
    # 迁移：geo_monitor_record 加 GEO/AEO 字段
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(geo_monitor_record)"))]
        if 'semantic_id' not in cols:
            conn.execute(text("ALTER TABLE geo_monitor_record ADD COLUMN semantic_id INTEGER"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_geo_monitor_semantic ON geo_monitor_record(semantic_id)"))
        if 'detect_type' not in cols:
            conn.execute(text("ALTER TABLE geo_monitor_record ADD COLUMN detect_type VARCHAR(20) DEFAULT 'brand'"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_geo_monitor_detect_type ON geo_monitor_record(detect_type)"))
        if 'recommend_count' not in cols:
            conn.execute(text("ALTER TABLE geo_monitor_record ADD COLUMN recommend_count INTEGER DEFAULT 0"))
        if 'cite_count' not in cols:
            conn.execute(text("ALTER TABLE geo_monitor_record ADD COLUMN cite_count INTEGER DEFAULT 0"))
        if 'aeo_confidence' not in cols:
            conn.execute(text("ALTER TABLE geo_monitor_record ADD COLUMN aeo_confidence FLOAT DEFAULT 0.0"))
        conn.commit()

    # 迁移：geo_semantic 加语义延伸字段（幂等）
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(geo_semantic)"))]
        if cols:
            if 'parent_id' not in cols:
                conn.execute(text("ALTER TABLE geo_semantic ADD COLUMN parent_id INTEGER"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_geo_semantic_parent ON geo_semantic(parent_id)"))
            if 'extend_type' not in cols:
                conn.execute(text("ALTER TABLE geo_semantic ADD COLUMN extend_type VARCHAR(20)"))
            if 'generated_at' not in cols:
                conn.execute(text("ALTER TABLE geo_semantic ADD COLUMN generated_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
        conn.commit()

    # 迁移：geo_doctor_profile 加个人品牌字段（幂等）
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(geo_doctor_profile)"))]
        if cols:
            doctor_brand_cols = {
                'avatar_url': "TEXT DEFAULT ''",
                'bio': "TEXT DEFAULT ''",
                'social_links': "TEXT DEFAULT '[]'",
                'personal_website': "TEXT DEFAULT ''",
                'registration_url': "TEXT DEFAULT ''",
                'clinic_hours': "TEXT DEFAULT '[]'",
            }
            for col, col_def in doctor_brand_cols.items():
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE geo_doctor_profile ADD COLUMN {col} {col_def}"))
        conn.commit()
