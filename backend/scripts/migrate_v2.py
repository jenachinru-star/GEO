"""
GEO V2 数据库迁移脚本（幂等，可重复运行）
用法：cd backend && python -m scripts.migrate_v2
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "geo.db")


def get_conn():
    return sqlite3.connect(DB_PATH)


def ensure_table(conn, table_name: str, create_sql: str):
    """幂等创建表"""
    conn.execute(create_sql)
    conn.commit()


def ensure_column(conn, table_name: str, column_name: str, column_def: str):
    """幂等添加列"""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
        conn.commit()
        print(f"  + 列 {table_name}.{column_name}")


def record_migration(conn, version: str):
    """记录迁移版本"""
    ensure_table(conn, "geo_schema_version", """
        CREATE TABLE IF NOT EXISTS geo_schema_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL,
            executed_at TEXT NOT NULL
        )
    """)
    cursor = conn.execute("SELECT COUNT(*) FROM geo_schema_version WHERE version=?", (version,))
    if cursor.fetchone()[0] == 0:
        conn.execute("INSERT INTO geo_schema_version (version, executed_at) VALUES (?, ?)",
                     (version, datetime.now().isoformat()))
        conn.commit()
        print(f"  + 迁移记录 {version}")


def migrate():
    conn = get_conn()
    print("开始数据库迁移...")

    # ===== 1. Workspace 相关表 =====
    print("[1/5] Workspace 相关表")
    ensure_table(conn, "geo_workspace", """
        CREATE TABLE IF NOT EXISTS geo_workspace (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT '',
            type TEXT NOT NULL DEFAULT 'personal',
            status TEXT NOT NULL DEFAULT 'active',
            timezone TEXT NOT NULL DEFAULT 'Asia/Shanghai',
            locale TEXT NOT NULL DEFAULT 'zh-CN',
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    ensure_table(conn, "geo_workspace_member", """
        CREATE TABLE IF NOT EXISTS geo_workspace_member (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'owner',
            status TEXT NOT NULL DEFAULT 'active',
            joined_at TEXT DEFAULT (datetime('now')),
            UNIQUE(workspace_id, user_id)
        )
    """)

    # ===== 2. AsyncTask 表 =====
    print("[2/5] AsyncTask 表")
    ensure_table(conn, "geo_async_task", """
        CREATE TABLE IF NOT EXISTS geo_async_task (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id INTEGER,
            task_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            progress INTEGER DEFAULT 0,
            progress_message TEXT DEFAULT '',
            payload_json TEXT DEFAULT '{}',
            result_json TEXT DEFAULT '{}',
            error_message TEXT DEFAULT '',
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            started_at TEXT,
            finished_at TEXT
        )
    """)
    # 索引
    conn.execute("CREATE INDEX IF NOT EXISTS idx_async_task_status ON geo_async_task(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_async_task_type ON geo_async_task(task_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_async_task_workspace ON geo_async_task(workspace_id)")
    conn.commit()

    # ===== ContentOpportunity 表 =====
    print("[ContentOpportunity] 内容机会表")
    ensure_table(conn, "geo_content_opportunity", """
        CREATE TABLE IF NOT EXISTS geo_content_opportunity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id INTEGER,
            doctor_id INTEGER,
            question_id INTEGER NOT NULL,
            opportunity_type TEXT NOT NULL,
            priority_score REAL DEFAULT 0.0,
            evidence_json TEXT DEFAULT '{}',
            status TEXT DEFAULT 'open',
            created_at TEXT DEFAULT (datetime('now')),
            resolved_at TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_opp_question ON geo_content_opportunity(question_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_opp_type ON geo_content_opportunity(opportunity_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_opp_status ON geo_content_opportunity(status)")
    conn.commit()

    # ===== 3. 现有表加列 =====
    print("[3/5] 现有表加列")
    # MonitorRecord 加证据字段
    ensure_column(conn, "geo_monitor_record", "mention_evidence", "TEXT DEFAULT ''")
    ensure_column(conn, "geo_monitor_record", "recommendation_evidence", "TEXT DEFAULT ''")
    ensure_column(conn, "geo_monitor_record", "citation_urls", "TEXT DEFAULT '[]'")
    ensure_column(conn, "geo_monitor_record", "analyzer_version", "TEXT DEFAULT 'rule_v1'")
    ensure_column(conn, "geo_monitor_record", "raw_sources_json", "TEXT DEFAULT '[]'")
    ensure_column(conn, "geo_monitor_record", "is_recommendation", "INTEGER DEFAULT 0")

    # ArticleDistribution 加状态机字段
    ensure_column(conn, "geo_article_distribution", "scheduled_at", "TEXT")
    ensure_column(conn, "geo_article_distribution", "failed_reason", "TEXT DEFAULT ''")
    ensure_column(conn, "geo_article_distribution", "retry_count", "INTEGER DEFAULT 0")
    ensure_column(conn, "geo_article_distribution", "publish_mode", "TEXT DEFAULT 'manual'")
    ensure_column(conn, "geo_article_distribution", "external_task_id", "TEXT DEFAULT ''")
    ensure_column(conn, "geo_article_distribution", "verified_at", "TEXT")

    # ===== 4. 为现有用户创建默认 Workspace =====
    print("[4/5] 初始化默认 Workspace")
    cursor = conn.execute("SELECT id, username FROM geo_user")
    users = cursor.fetchall()
    for user_id, username in users:
        # 检查是否已有owner角色的workspace
        cursor2 = conn.execute(
            "SELECT w.id FROM geo_workspace w JOIN geo_workspace_member m ON w.id=m.workspace_id "
            "WHERE m.user_id=? AND m.role='owner'", (user_id,))
        if cursor2.fetchone() is None:
            ws_name = f"{username or '用户'}的个人工作台"
            conn.execute("INSERT INTO geo_workspace (name, type, created_by) VALUES (?, 'personal', ?)",
                         (ws_name, user_id))
            ws_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("INSERT INTO geo_workspace_member (workspace_id, user_id, role) VALUES (?, ?, 'owner')",
                         (ws_id, user_id))
            print(f"  + 为用户 {user_id}({username}) 创建 Workspace {ws_id}")
    conn.commit()

    # ===== 5. 记录迁移版本 =====
    print("[5/5] 记录迁移版本")
    record_migration(conn, "v2.0_base")

    print("✅ 数据库迁移完成")
    conn.close()


if __name__ == "__main__":
    migrate()
