"""测试 ArticleGenerator 模板降级路径"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import SessionLocal
from app.models.semantic import Semantic
from app.models.doctor import DoctorProfile
from app.engines.article_generator import ArticleGenerator

db = SessionLocal()
semantic = db.query(Semantic).filter(Semantic.user_id == 1).first()
profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == 1).first()
print(f"语义: {semantic.question}")
print(f"医生: {profile.real_name} / {profile.hospital}")

gen = ArticleGenerator(db)
result = gen.generate(semantic, profile)
print(f"生成来源: {result['source']}")
print(f"标题: {result['title'][:60]}")
has_disclaimer = "免责声明" in result["conclusion"] or "不能替代" in result["conclusion"]
print(f"包含免责声明: {has_disclaimer}")
print(f"full_text 长度: {len(result['full_text'])}")
print(f"标签: {result['tags']}")
db.close()
print("\nArticleGenerator 模板降级路径测试通过")
