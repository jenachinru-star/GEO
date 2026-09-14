"""llms.txt 生成器
为医生生成AI爬虫友好的llms.txt，帮助AI快速识别医生信息
参考：https://llmstxt.org/ 新兴标准
"""
from app.models.doctor import DoctorProfile
from app.models.semantic import Semantic
from app.models.article import ArticleDraft


class LlmsGenerator:
    def generate(self, profile: DoctorProfile, semantics: list, articles: list) -> str:
        lines = []

        # 标题
        lines.append(f"# {profile.city}{profile.hospital}{profile.department}{profile.real_name}医生")
        lines.append("")

        # 医生简介
        lines.append("## 医生简介")
        lines.append(f"- 姓名：{profile.real_name}")
        lines.append(f"- 职称：{profile.title}")
        lines.append(f"- 医院：{profile.hospital}")
        lines.append(f"- 科室：{profile.department}")
        lines.append(f"- 城市：{profile.province}{profile.city}")
        lines.append(f"- 专长：{profile.specialty}")
        if profile.awards:
            lines.append(f"- 荣誉：{profile.awards}")
        if profile.case_history:
            lines.append(f"- 简介：{profile.case_history}")
        lines.append("")

        # 语义列表（患者常问问题）
        lines.append("## 患者常问问题（语义库）")
        for s in semantics:
            if s.is_active:
                lines.append(f"- {s.question}")
        lines.append("")

        # 科普文章列表
        if articles:
            lines.append("## 科普文章")
            for a in articles[:20]:  # 最多20篇
                lines.append(f"- {a.title}")
                if a.platform:
                    lines.append(f"  - 发布平台：{a.platform}")
        lines.append("")

        # 实体一致性声明
        lines.append("## 实体一致性声明")
        lines.append(f"全网统一署名格式：{profile.city}{profile.hospital}{profile.department}{profile.real_name}医生")
        lines.append("")

        return "\n".join(lines)


llms_generator = LlmsGenerator()
