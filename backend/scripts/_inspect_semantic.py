import sqlite3
conn = sqlite3.connect(r'C:\Users\jenac\Desktop\GEO\backend\data\geo.db')
c = conn.cursor()

print('=== geo_semantic 表结构 ===')
c.execute('PRAGMA table_info(geo_semantic)')
for row in c.fetchall():
    print(row)

print()
print('=== 语义数据统计 ===')
c.execute('SELECT COUNT(*) FROM geo_semantic')
print('总数:', c.fetchone()[0])
c.execute('SELECT category, COUNT(*) FROM geo_semantic GROUP BY category')
print('按category:', c.fetchall())
c.execute('SELECT extend_type, COUNT(*) FROM geo_semantic WHERE extend_type IS NOT NULL GROUP BY extend_type')
print('按extend_type:', c.fetchall())
c.execute('SELECT is_active, COUNT(*) FROM geo_semantic GROUP BY is_active')
print('按is_active:', c.fetchall())

print()
print('=== 全部语义 ===')
c.execute('SELECT id, user_id, question, category, parent_id, extend_type, geo_rate, aeo_rate, article_count FROM geo_semantic ORDER BY id')
for row in c.fetchall():
    print(row)

print()
print('=== doctor profile ===')
c.execute('SELECT * FROM geo_doctor_profile')
cols = [d[0] for d in c.description]
for row in c.fetchall():
    for col, val in zip(cols, row):
        if col in ('real_name','title','province','city','hospital','department','specialty'):
            print(f'  {col}: {val}')

print()
print('=== 文章草稿与语义关联 ===')
c.execute('SELECT id, user_id, semantic_id, title, status FROM geo_article_draft ORDER BY id')
for row in c.fetchall():
    print(row)

print()
print('=== monitor_record 中 semantic_id 非空的记录 ===')
c.execute('SELECT COUNT(*) FROM geo_monitor_record WHERE semantic_id IS NOT NULL')
print('semantic记录数:', c.fetchone()[0])
c.execute('SELECT semantic_id, platform_code, mentioned, rank, cite_count, detect_date FROM geo_monitor_record WHERE semantic_id IS NOT NULL ORDER BY id DESC LIMIT 10')
for row in c.fetchall():
    print(row)

conn.close()
