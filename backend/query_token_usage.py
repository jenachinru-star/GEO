"""查询 token 消耗数据"""
import sqlite3

conn = sqlite3.connect('data/geo.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 先看表结构
cur.execute('PRAGMA table_info(geo_llm_usage_log)')
print('=== 表结构 ===')
for r in cur.fetchall():
    print(f'  {r["name"]:20s} {r["type"]}')
print()

# 1. 总览
cur.execute('SELECT COUNT(*) as cnt, COALESCE(SUM(total_tokens),0) as total, COALESCE(SUM(prompt_tokens),0) as prompt, COALESCE(SUM(completion_tokens),0) as completion FROM geo_llm_usage_log')
row = cur.fetchone()
print('=== 总览 ===')
print(f'总调用次数: {row["cnt"]}')
print(f'总 Token: {row["total"]}')
print(f'  Prompt Token: {row["prompt"]}')
print(f'  Completion Token: {row["completion"]}')
print()

# 2. 按任务类型
cur.execute('SELECT task_type, COUNT(*) as cnt, COALESCE(SUM(total_tokens),0) as total, COALESCE(AVG(total_tokens),0) as avg FROM geo_llm_usage_log GROUP BY task_type ORDER BY total DESC')
print('=== 按任务类型 ===')
for r in cur.fetchall():
    tt = r["task_type"] if r["task_type"] else "(空)"
    print(f'{tt:20s} 调用:{r["cnt"]:3d}  总Token:{r["total"]:8d}  平均:{int(r["avg"]):6d}')
print()

# 3. 按平台
cur.execute('SELECT platform, model, COUNT(*) as cnt, COALESCE(SUM(total_tokens),0) as total, COALESCE(AVG(total_tokens),0) as avg FROM geo_llm_usage_log GROUP BY platform, model ORDER BY total DESC')
print('=== 按平台/模型 ===')
for r in cur.fetchall():
    print(f'{r["platform"]:10s} {r["model"]:30s} 调用:{r["cnt"]:3d}  总Token:{r["total"]:8d}  平均:{int(r["avg"]):6d}')
print()

# 4. 按用户
cur.execute('SELECT user_id, COUNT(*) as cnt, COALESCE(SUM(total_tokens),0) as total FROM geo_llm_usage_log GROUP BY user_id ORDER BY total DESC')
print('=== 按用户 ===')
for r in cur.fetchall():
    uid = str(r["user_id"]) if r["user_id"] else "(空)"
    print(f'用户ID:{uid:10s}  调用:{r["cnt"]:3d}  总Token:{r["total"]:8d}')
print()

# 5. 最近20条详细记录
cur.execute('SELECT * FROM geo_llm_usage_log ORDER BY id DESC LIMIT 20')
print('=== 最近20条详细记录 ===')
for r in cur.fetchall():
    tt = r["task_type"] if r["task_type"] else "(空)"
    print(f'#{r["id"]:2d} {r["created_at"]} 平台:{r["platform"]:8s} 任务:{tt:12s} Token:{r["total_tokens"]:6d} (in:{r["prompt_tokens"]},out:{r["completion_tokens"]}) 耗时:{r["latency_ms"]}ms 成功:{r["success"]}')

conn.close()
