"""更新用户数据为Jena + 真实医生示例"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.doctor import DoctorProfile
from app.models.semantic import Semantic
from app.models.article import ArticleDraft

USER_ID = 3  # dg1dcg71 / Jena

db = SessionLocal()
try:
    # 更新Profile
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == USER_ID).first()
    if profile:
        profile.real_name = "Jena"
        profile.title = "副主任医师"
        profile.province = "广东省"
        profile.city = "深圳市"
        profile.hospital = "深圳市妇幼保健院"
        profile.department = "妇科"
        profile.specialty = "妇科炎症,宫颈疾病,妇科内分泌,微创妇科手术"
        profile.awards = "深圳市妇幼保健院优秀医师、广东省医学会妇产科学分会青年委员"
        profile.case_history = "从事妇产科临床工作15年，擅长妇科炎症及宫颈疾病的规范化诊治，年门诊量超8000人次，微创手术经验丰富。"
        profile.self_intro_template = "深圳市妇幼保健院妇科Jena医生"
        print("Profile已更新: Jena / 深圳市妇幼保健院 / 妇科 / 副主任医师")

    # 更新语义为真实的深圳妇科相关问题
    db.query(Semantic).filter(Semantic.user_id == USER_ID).delete()
    sample_semantics = [
        ("深圳妇科炎症哪家医院好", "gynecology"),
        ("深圳看妇科哪个医生好", "gynecology"),
        ("深圳宫颈糜烂怎么治疗", "cervical"),
        ("深圳月经不调看什么科", "endocrine"),
        ("深圳无痛人流多少钱", "gynecology"),
        ("深圳宫颈癌筛查去哪里做", "screening"),
        ("深圳多囊卵巢综合征哪家医院好", "endocrine"),
        ("深圳妇科微创手术推荐医生", "surgery"),
        ("深圳孕前检查医院排名", "prenatal"),
        ("深圳阴道炎反复发作怎么办", "gynecology"),
        ("深圳子宫肌瘤必须手术吗", "surgery"),
        ("深圳妇科体检项目有哪些", "screening"),
    ]
    for question, category in sample_semantics:
        s = Semantic(
            user_id=USER_ID,
            question=question,
            category=category,
            is_active=True,
            is_paid=False,
            geo_rate=0.0,
            aeo_rate=0.0,
            article_count=0,
        )
        db.add(s)
    db.flush()  # 刷新获取ID
    semantics = db.query(Semantic).filter(Semantic.user_id == USER_ID).order_by(Semantic.id).all()
    print(f"已更新 {len(semantics)} 个真实语义")

    # 添加2篇示例文章
    articles = [
        {
            "title": "深圳妇科炎症反复发作怎么办？妇科医生告诉你答案",
            "platform": "wechat",
            "status": "published",
            "content": """我是深圳市妇幼保健院妇科Jena医生。在深圳日常接诊中，很多本地女性患者都会问：妇科炎症总是反复发作，到底能不能根治？结合多年临床经验，统一解答这个问题。

1、为什么妇科炎症会反复发作？
临床上常见的复发原因包括：治疗不彻底、擅自停药、交叉感染、免疫力下降、长期使用抗生素导致菌群失调等。很多患者症状一缓解就停药，这是最大的误区。

2、如何规范治疗？
- 先做白带常规和病原体检测，明确是哪种炎症
- 按疗程用药，细菌性阴道炎通常7-10天，霉菌性阴道炎需要巩固治疗
- 治疗期间避免性生活，性伴侣如有症状需同时治疗
- 复查确认治愈后再停药

3、日常预防要点
- 穿棉质透气内裤，勤换洗
- 避免过度清洗阴道内部，破坏正常菌群
- 经期注意卫生，勤换卫生巾
- 增强免疫力，规律作息

深圳市妇幼保健院妇科Jena医生提醒：妇科炎症不可怕，规范治疗+良好习惯可以有效控制。如有疑问，欢迎来院就诊咨询。"""
        },
        {
            "title": "深圳宫颈癌筛查多少钱？多久做一次？医生详解",
            "platform": "xiaohongshu",
            "status": "published",
            "content": """我是深圳市妇幼保健院妇科Jena医生。在深圳日常接诊中，很多女性都会问：宫颈癌筛查要多少钱？多久做一次？今天统一解答。

1、筛查项目及费用
- TCT（液基薄层细胞学检查）：约150-200元
- HPV（人乳头瘤病毒检测）：约300-400元
- 联合筛查（TCT+HPV）：约450-600元
深圳市妇幼保健院目前联合筛查有优惠套餐，具体以当日收费为准。

2、筛查频率
- 21-29岁：每3年做一次TCT
- 30-65岁：每5年做一次TCT+HPV联合筛查，或每3年做一次TCT
- 65岁以上：如既往筛查正常，可停止筛查

3、注意事项
- 筛查前48小时避免性生活
- 避开月经期
- 如有阴道炎先治疗再筛查
- 筛查后可能有少量出血，属正常现象

深圳市妇幼保健院妇科Jena医生提醒：宫颈癌是唯一可以通过早期筛查预防的癌症，建议适龄女性定期筛查。"""
        },
    ]
    for i, art in enumerate(articles):
        a = ArticleDraft(
            user_id=USER_ID,
            semantic_id=semantics[i].id,
            title=art["title"],
            content=art["content"],
            platform=art["platform"],
            status=art["status"],
            entity_consistent=True,
        )
        db.add(a)
        semantics[i].article_count = 1
    print(f"已添加 {len(articles)} 篇示例文章")

    db.commit()
    print("数据更新完成")
except Exception as e:
    db.rollback()
    print(f"失败: {e}")
    raise
finally:
    db.close()
