"""一次性迁移：给全局表加user_id字段，并将现有数据归属到admin用户"""
import sqlite3
import sys

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "./data/geo.db"
ADMIN_USER_ID = 1  # 假设admin是id=1，执行前确认

def migrate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    tables = ["geo_question", "geo_content", "geo_knowledge", "geo_competitor"]
    for table in tables:
        # 检查字段是否已存在
        cols = [row[1] for row in c.execute(f"PRAGMA table_info({table})").fetchall()]
        if "user_id" not in cols:
            c.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER DEFAULT {ADMIN_USER_ID}")
            c.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_user_id ON {table}(user_id)")
            print(f"  {table}: 已添加user_id字段和索引")
        else:
            print(f"  {table}: user_id已存在，跳过")
    conn.commit()
    conn.close()
    print("迁移完成")

if __name__ == "__main__":
    migrate()
