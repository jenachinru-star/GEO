"""T06 数据库验证脚本"""
import sqlite3

conn = sqlite3.connect('data/geo.db')
tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()]
print('表列表:', tables)
print()

# 检查关键新表
for t in ['geo_workspace', 'geo_workspace_member', 'geo_async_task', 'geo_schema_version']:
    assert t in tables, f'缺少表: {t}'
    print(f'  OK 表存在: {t}')
print()

# 检查 monitor_record 新列
cols = [r[1] for r in conn.execute('PRAGMA table_info(geo_monitor_record)').fetchall()]
for c in ['mention_evidence', 'recommendation_evidence', 'citation_urls', 'analyzer_version', 'is_recommendation']:
    assert c in cols, f'缺少列: geo_monitor_record.{c}'
    print(f'  OK 列存在: geo_monitor_record.{c}')
print()

# 检查 distribution 新列
cols = [r[1] for r in conn.execute('PRAGMA table_info(geo_article_distribution)').fetchall()]
for c in ['scheduled_at', 'failed_reason', 'retry_count', 'publish_mode', 'external_task_id', 'verified_at']:
    assert c in cols, f'缺少列: geo_article_distribution.{c}'
    print(f'  OK 列存在: geo_article_distribution.{c}')
print()

# 检查每个用户有默认Workspace
ws_count = conn.execute('SELECT COUNT(*) FROM geo_workspace').fetchone()[0]
user_count = conn.execute('SELECT COUNT(*) FROM geo_user').fetchone()[0]
print(f'用户数: {user_count}, Workspace数: {ws_count}')

rows = conn.execute("""
    SELECT u.id, u.username, COUNT(w.id) as ws_count
    FROM geo_user u
    LEFT JOIN geo_workspace_member m ON u.id = m.user_id AND m.role = 'owner'
    LEFT JOIN geo_workspace w ON m.workspace_id = w.id
    GROUP BY u.id
""").fetchall()
for r in rows:
    print(f'  用户 {r[0]}({r[1]}): owner Workspace数={r[2]}')

conn.close()
print()
print('=== 数据库验证全部通过 ===')
