"""数据库迁移脚本：给 geo_user 表添加缺失的字段"""
import sqlite3

conn = sqlite3.connect('data/geo.db')
cur = conn.cursor()

# 获取现有字段
cur.execute('PRAGMA table_info(geo_user)')
existing_columns = {r[1] for r in cur.fetchall()}
print(f'现有字段: {existing_columns}')

# 需要添加的字段
columns_to_add = [
    ('email', 'VARCHAR(200)', None),
    ('last_login_at', 'DATETIME', None),
    ('login_count', 'INTEGER', '0'),
]

for col_name, col_type, default in columns_to_add:
    if col_name not in existing_columns:
        if default is not None:
            sql = f'ALTER TABLE geo_user ADD COLUMN {col_name} {col_type} DEFAULT {default}'
        else:
            sql = f'ALTER TABLE geo_user ADD COLUMN {col_name} {col_type}'
        print(f'执行: {sql}')
        cur.execute(sql)
        print(f'  ✅ 添加字段 {col_name}')
    else:
        print(f'  ⏭️  字段 {col_name} 已存在，跳过')

conn.commit()

# 验证
cur.execute('PRAGMA table_info(geo_user)')
print('\n=== 迁移后 geo_user 表字段 ===')
for r in cur.fetchall():
    print(f'  {r[1]} ({r[2]}) default={r[4]}')

conn.close()
print('\n✅ 数据库迁移完成')
