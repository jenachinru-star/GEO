"""数据库迁移脚本：给 geo_platform 表添加扩展字段"""
import sqlite3

conn = sqlite3.connect('data/geo.db')
cur = conn.cursor()

# 查看 geo_platform 表现有字段
cur.execute('PRAGMA table_info(geo_platform)')
existing_columns = {r[1] for r in cur.fetchall()}
print(f'geo_platform 表现有字段: {existing_columns}')

# 需要添加的字段
columns_to_add = [
    ('priority', 'INTEGER', '0'),
    ('timeout', 'INTEGER', '30'),
    ('max_tokens', 'INTEGER', '2000'),
    ('temperature', 'FLOAT', '0.3'),
    ('description', 'VARCHAR(500)', "''"),
    ('platform_type', 'VARCHAR(50)', "'openai_compatible'"),
    ('extra_config', 'TEXT', "'{}'"),
]

for col_name, col_type, default in columns_to_add:
    if col_name not in existing_columns:
        sql = f'ALTER TABLE geo_platform ADD COLUMN {col_name} {col_type} DEFAULT {default}'
        print(f'执行: {sql}')
        cur.execute(sql)
        print(f'  ✅ 添加字段 {col_name}')
    else:
        print(f'  ⏭️  字段 {col_name} 已存在，跳过')

conn.commit()

# 验证
cur.execute('PRAGMA table_info(geo_platform)')
print('\n=== 迁移后 geo_platform 表字段 ===')
for r in cur.fetchall():
    print(f'  {r[1]} ({r[2]}) default={r[4]}')

conn.close()
print('\n✅ geo_platform 表迁移完成')
