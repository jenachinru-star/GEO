"""阶段四C数据库迁移：创建对标账号/审计日志/竞品分析表
运行方式：cd backend && C:\\Users\\jenac\\miniconda3\\python.exe -m migrations.add_phase4c_tables
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base
from app.models.benchmark_account import BenchmarkAccount, BenchmarkArticle
from app.models.audit_log import AuditLog
from app.models.competitor_analysis import CompetitorAnalysis


def upgrade():
    print("创建阶段四C数据表...")
    Base.metadata.create_all(bind=engine, tables=[
        BenchmarkAccount.__table__,
        BenchmarkArticle.__table__,
        AuditLog.__table__,
        CompetitorAnalysis.__table__,
    ])
    print("✅ 表创建完成")
    print("  - geo_benchmark_account (对标账号)")
    print("  - geo_benchmark_article (对标文章)")
    print("  - geo_audit_log (审计日志)")
    print("  - geo_competitor_analysis (竞品分析结果)")


if __name__ == "__main__":
    upgrade()
