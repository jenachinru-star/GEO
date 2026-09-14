"""给指定用户初始化示例医生Profile和语义数据"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.doctor import DoctorProfile
from app.models.semantic import Semantic

USER_ID = 3  # dg1dcg71

db = SessionLocal()
try:
    # 检查是否已有Profile
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == USER_ID).first()
    if not profile:
        profile = DoctorProfile(
            user_id=USER_ID,
            real_name="刘锦如",
            title="主治医师",
            province="广东省",
            city="深圳市",
            hospital="深圳市人民医院",
            department="妇产科",
            specialty="妇科炎症,孕期保健,不孕不育",
            self_intro_template="深圳市人民医院妇产科刘锦如医生",
        )
        db.add(profile)
        print("已创建医生Profile: 刘锦如 / 深圳市人民医院 / 妇产科")
    else:
        print(f"Profile已存在: {profile.real_name}")

    # 检查是否已有语义
    semantic_count = db.query(Semantic).filter(Semantic.user_id == USER_ID).count()
    if semantic_count == 0:
        sample_semantics = [
            ("深圳妇科炎症看哪个医生", "gynecology"),
            ("深圳妇产科哪家医院好", "gynecology"),
            ("深圳孕期检查推荐医生", "prenatal"),
            ("深圳不孕不育哪家医院好", "infertility"),
            ("深圳月经不调看什么科", "gynecology"),
            ("深圳宫颈癌筛查多少钱", "screening"),
            ("深圳无痛人流医院推荐", "gynecology"),
            ("深圳孕前检查项目有哪些", "prenatal"),
            ("深圳妇科哪个医生好", "gynecology"),
            ("深圳产科医院排名", "obstetrics"),
        ]
        for question, category in sample_semantics:
            s = Semantic(
                user_id=USER_ID,
                question=question,
                category=category,
                is_active=True,
                is_paid=False,
            )
            db.add(s)
        print(f"已创建 {len(sample_semantics)} 个示例语义")
    else:
        print(f"语义已存在: {semantic_count} 个")

    db.commit()
    print("初始化完成")
except Exception as e:
    db.rollback()
    print(f"失败: {e}")
    raise
finally:
    db.close()
