"""D1迁移：重建geo_monitor_record表，唯一约束从question_id改为semantic_id，question_id改为可空"""
import sqlite3
import sys

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "./data/geo.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 检查当前约束名
    constraints = c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='geo_monitor_record'").fetchone()[0]
    if 'uix_semantic_platform_date_round' in constraints:
        print("已迁移过，跳过")
        conn.close()
        return

    print("开始重建geo_monitor_record表...")
    count_before = c.execute("SELECT COUNT(*) FROM geo_monitor_record").fetchone()[0]
    print(f"  迁移前行数: {count_before}")

    c.execute("BEGIN")

    # 创建新表
    c.execute("""
        CREATE TABLE geo_monitor_record_new (
            id INTEGER NOT NULL,
            question_id INTEGER,
            platform_code VARCHAR(50) NOT NULL,
            rank INTEGER,
            mentioned BOOLEAN,
            sentiment FLOAT,
            raw_answer TEXT,
            detect_date VARCHAR(20) NOT NULL,
            detect_round INTEGER,
            detect_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            semantic_id INTEGER,
            detect_type VARCHAR(20) DEFAULT 'brand',
            recommend_count INTEGER DEFAULT 0,
            cite_count INTEGER DEFAULT 0,
            aeo_confidence FLOAT DEFAULT 0.0,
            mention_evidence TEXT DEFAULT '',
            recommendation_evidence TEXT DEFAULT '',
            citation_urls TEXT DEFAULT '[]',
            analyzer_version TEXT DEFAULT 'rule_v1',
            raw_sources_json TEXT DEFAULT '[]',
            is_recommendation INTEGER DEFAULT 0,
            PRIMARY KEY (id),
            CONSTRAINT uix_semantic_platform_date_round UNIQUE (semantic_id, platform_code, detect_date, detect_round),
            FOREIGN KEY(question_id) REFERENCES geo_question (id)
        )
    """)

    # 复制数据
    c.execute("""
        INSERT INTO geo_monitor_record_new
        SELECT id, question_id, platform_code, rank, mentioned, sentiment, raw_answer,
               detect_date, detect_round, detect_time, created_at, semantic_id, detect_type,
               recommend_count, cite_count, aeo_confidence, mention_evidence,
               recommendation_evidence, citation_urls, analyzer_version, raw_sources_json,
               is_recommendation
        FROM geo_monitor_record
    """)

    # 删除旧表
    c.execute("DROP TABLE geo_monitor_record")

    # 重命名新表
    c.execute("ALTER TABLE geo_monitor_record_new RENAME TO geo_monitor_record")

    # 重建索引
    c.execute("CREATE INDEX ix_geo_monitor_record_question_id ON geo_monitor_record (question_id)")
    c.execute("CREATE INDEX ix_geo_monitor_record_id ON geo_monitor_record (id)")
    c.execute("CREATE INDEX ix_geo_monitor_record_platform_code ON geo_monitor_record (platform_code)")
    c.execute("CREATE INDEX ix_geo_monitor_record_detect_date ON geo_monitor_record (detect_date)")
    c.execute("CREATE INDEX idx_geo_monitor_semantic ON geo_monitor_record(semantic_id)")
    c.execute("CREATE INDEX idx_geo_monitor_detect_type ON geo_monitor_record(detect_type)")

    c.execute("COMMIT")

    count_after = c.execute("SELECT COUNT(*) FROM geo_monitor_record").fetchone()[0]
    print(f"  迁移后行数: {count_after}")

    # 验证约束
    new_sql = c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='geo_monitor_record'").fetchone()[0]
    assert 'uix_semantic_platform_date_round' in new_sql, "约束未更新!"
    assert 'uix_question_platform_date_round' not in new_sql, "旧约束仍存在!"
    print("  约束验证通过: uix_semantic_platform_date_round")

    conn.close()
    print("D1迁移完成")

if __name__ == "__main__":
    migrate()
