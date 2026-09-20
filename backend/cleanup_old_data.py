"""清理旧脏数据：删除 user_id 为空或 task_type 为 other 的测试数据"""
import sqlite3

conn = sqlite3.connect('data/geo.db')
cur = conn.cursor()

# 查看清理前的数据
cur.execute('SELECT COUNT(*) FROM geo_llm_usage_log')
total_before = cur.fetchone()[0]
print(f'清理前总记录数: {total_before}')

# 删除 user_id 为空的记录
cur.execute('DELETE FROM geo_llm_usage_log WHERE user_id IS NULL')
deleted_null = cur.rowcount
print(f'删除 user_id 为空的记录: {deleted_null} 条')

# 删除 task_type 为 other 的记录（旧测试数据）
cur.execute('DELETE FROM geo_llm_usage_log WHERE task_type = ?', ('other',))
deleted_other = cur.rowcount
print(f'删除 task_type 为 other 的记录: {deleted_other} 条')

conn.commit()

# 查看清理后的数据
cur.execute('SELECT COUNT(*) FROM geo_llm_usage_log')
total_after = cur.fetchone()[0]
print(f'清理后总记录数: {total_after}')

# 查看剩余记录
cur.execute('SELECT id, created_at, platform, task_type, total_tokens, user_id FROM geo_llm_usage_log ORDER BY id DESC LIMIT 10')
print('\n剩余记录:')
for r in cur.fetchall():
    print(f'  #{r[0]} {r[1]} 平台:{r[2]} 任务:{r[3]} Token:{r[4]} 用户:{r[5]}')

conn.close()
print('\n✅ 旧脏数据清理完成')
