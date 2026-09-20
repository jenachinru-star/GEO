"""检查数据库结构，确认需要迁移的字段"""
import sqlite3

conn = sqlite3.connect('data/geo.db')
cur = conn.cursor()

# 查看 geo_user 表现有字段
cur.execute('PRAGMA table_info(geo_user)')
print('=== geo_user 表现有字段 ===')
for r in cur.fetchall():
    print(f'  {r[1]} ({r[2]})')

# 查看所有表
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('\n=== 数据库所有表 ===')
for r in cur.fetchall():
    print(f'  {r[0]}')

# 检查 geo_verification_code 表是否存在
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='geo_verification_code'")
vc = cur.fetchone()
print(f'\ngeo_verification_code 表存在: {bool(vc)}')

# 检查 geo_llm_usage_log 表是否存在
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='geo_llm_usage_log'")
ul = cur.fetchone()
print(f'geo_llm_usage_log 表存在: {bool(ul)}')

# 检查 geo_auth_ticket 表是否存在
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='geo_auth_ticket'")
at = cur.fetchone()
print(f'geo_auth_ticket 表存在: {bool(at)}')

conn.close()
