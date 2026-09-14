# -*- coding: utf-8 -*-
"""批量修复语义问题，确保以问号结尾"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "geo.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.execute("SELECT id, question FROM geo_semantic")
rows = cursor.fetchall()

fixed = 0
for sid, question in rows:
    original = question
    question = question.strip()
    if not question.endswith('？') and not question.endswith('?'):
        question = question + '？'
        conn.execute("UPDATE geo_semantic SET question=? WHERE id=?", (question, sid))
        print(f"  [{sid}] {original} -> {question}")
        fixed += 1

conn.commit()
print(f"\n✅ 修复完成，共修复 {fixed} 条语义问题")
conn.close()
