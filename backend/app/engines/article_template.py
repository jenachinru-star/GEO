"""GEO/AEO 文章模板引擎
根据语义和医生Profile自动生成标准结构的文章模板
"""
from dataclasses import dataclass
from typing import Optional
from app.models.doctor import DoctorProfile
from app.models.semantic import Semantic


@dataclass
class ArticleTemplate:
    title: str
    intro: str
    body: str
    conclusion: str
    tags: list[str]
    full_text: str


class ArticleTemplateEngine:
    def generate(self, semantic: Semantic, profile: DoctorProfile) -> ArticleTemplate:
        """根据语义和医生Profile生成文章模板"""
        city = profile.city or ""
        hospital = profile.hospital or ""
        department = profile.department or ""
        name = profile.real_name or ""
        title_name = profile.title or ""

        # 标题：AEO问句式 + GEO地域
        title = self._gen_title(semantic.question, city, department)

        # 首段：实体锚定 + GEO本地化
        intro = (
            f"我是{city}{hospital}{department}{name}医生。"
            f"在{city}日常接诊中，很多本地患者都会问：{semantic.question}？"
            f"结合{title_name}多年临床经验，统一解答这个问题。"
        )

        # 正文：分点回答，AEO友好短句
        body = self._gen_body(semantic.category, semantic.question)

        # 文末：就诊说明 + 异地咨询
        conclusion = (
            f"{city}{hospital}{department}{name}医生提醒："
            f"以上内容仅供科普参考，具体诊疗请遵医嘱。"
            f"{city}本地患者可来院就诊，异地患者可在线咨询。"
        )

        # 标签：地域病种标签
        tags = [
            f"#{city}{department}",
            f"#{semantic.question.replace('？','').replace('?','')}",
            f"#{hospital}",
        ]

        full_text = f"{title}\n\n{intro}\n\n{body}\n\n{conclusion}\n\n{' '.join(tags)}"

        return ArticleTemplate(
            title=title, intro=intro, body=body,
            conclusion=conclusion, tags=tags, full_text=full_text
        )

    def _gen_title(self, question: str, city: str, department: str) -> str:
        """生成AEO问句式标题"""
        # 如果问题已经是问句式，直接用
        if any(q in question for q in ['怎么', '如何', '为什么', '多少', '哪里', '哪个', '什么', '吗', '呢']):
            return f"{question}？{department}医生解答"
        return f"{city}{department}：{question}？医生详解"

    def _gen_body(self, category: str, question: str) -> str:
        """根据语义类别生成正文框架"""
        templates = {
            'gynecology': (
                "1、为什么会出现这个问题？\n"
                "   - 常见原因包括...\n"
                "   - 诱发因素有...\n\n"
                "2、如何规范治疗？\n"
                "   - 先做相关检查明确诊断\n"
                "   - 按疗程用药，症状缓解后继续巩固\n"
                "   - 定期复查\n\n"
                "3、日常预防要点\n"
                "   - 注意个人卫生\n"
                "   - 增强免疫力，规律作息\n"
                "   - 避免过度清洗"
            ),
            'screening': (
                "1、筛查项目及费用\n"
                "   - 项目一：约XX元\n"
                "   - 项目二：约XX元\n\n"
                "2、筛查频率\n"
                "   - XX岁：每X年一次\n"
                "   - XX岁以上：...\n\n"
                "3、注意事项\n"
                "   - 筛查前XX小时避免...\n"
                "   - 避开特殊时期\n"
                "   - 如有不适先治疗再筛查"
            ),
            'surgery': (
                "1、什么情况下需要手术？\n"
                "   - 手术指征包括...\n"
                "   - 保守治疗无效时考虑\n\n"
                "2、手术方式有哪些？\n"
                "   - 微创手术：...\n"
                "   - 传统手术：...\n\n"
                "3、术后恢复注意事项\n"
                "   - 术后X天内...\n"
                "   - 定期复查\n"
                "   - 如有异常及时就诊"
            ),
            'endocrine': (
                "1、常见原因有哪些？\n"
                "   - 内分泌因素\n"
                "   - 生活方式因素\n\n"
                "2、如何调理？\n"
                "   - 药物治疗\n"
                "   - 生活方式调整\n\n"
                "3、什么时候需要就医？\n"
                "   - 出现以下情况及时就诊\n"
                "   - 定期复查激素水平"
            ),
        }
        return templates.get(category, templates['gynecology'])


article_template_engine = ArticleTemplateEngine()
