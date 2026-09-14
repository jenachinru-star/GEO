"""最终全量后端导入验证"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.main
import app.worker.worker
import app.services.distribution_service
import app.engines.llm_analyzer
import app.engines.geo_aeo_analyzer
import app.engines.collector
import app.engines.opportunity_engine
import app.engines.article_generator
import app.api.task
import app.api.geo
import app.api.monitor
import app.api.distribution
import app.api.opportunity
import app.api.image
import app.api.template
import app.models.workspace
import app.models.task
import app.models.content_opportunity
import app.adapters
from app.main import app

schema = app.openapi()
print("=== 全部后端模块导入成功 ===")
print("API 端点总数:", len(schema["paths"]))
print("路由总数:", len(app.routes))

# 列出所有新增端点
new_prefixes = ["/task", "/opportunity", "/image"]
print("\n=== T05-T09 新增端点 ===")
for path, methods in sorted(schema["paths"].items()):
    if any(path.startswith(f"/api/v1{p}") for p in new_prefixes):
        for m in methods:
            print(f"  {m.upper()} {path}")
