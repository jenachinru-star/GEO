"""实体一致性校验引擎
核心逻辑：AI会因为医生信息在不同平台不一致而降权。
校验医生Profile和文章中的实体信息是否统一。
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import re


@dataclass
class ValidationIssue:
    """校验问题"""
    level: str  # error / warning / info
    field: str  # 哪个字段有问题
    message: str  # 问题描述
    suggestion: str  # 修复建议


@dataclass
class ValidationResult:
    """校验结果"""
    score: int  # 0-100
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(i.level == "error" for i in self.issues)

    def to_dict(self) -> Dict:
        return {
            "score": self.score,
            "passed": self.passed,
            "issues": [
                {"level": i.level, "field": i.field, "message": i.message, "suggestion": i.suggestion}
                for i in self.issues
            ]
        }


class EntityValidator:
    """实体一致性校验器"""

    # 标准自我介绍格式：XX市XX医院XX科XX医生
    STANDARD_PATTERN = r'^(.+市)?(.+医院)(.+科)(.+医生)$'

    def validate_profile(self, profile) -> ValidationResult:
        """校验医生Profile的实体一致性

        Args:
            profile: DoctorProfile对象
        Returns:
            ValidationResult
        """
        issues: List[ValidationIssue] = []
        score = 100

        real_name = (profile.real_name or "").strip()
        hospital = (profile.hospital or "").strip()
        department = (profile.department or "").strip()
        city = (profile.city or "").strip()
        title = (profile.title or "").strip()
        self_intro = (profile.self_intro_template or "").strip()

        # 1. 四要素完整性检查
        if not real_name:
            issues.append(ValidationIssue("error", "real_name", "医生姓名为空", "请填写真实姓名"))
            score -= 25
        if not hospital:
            issues.append(ValidationIssue("error", "hospital", "医院名称为空", "请填写所在医院全称"))
            score -= 25
        if not department:
            issues.append(ValidationIssue("error", "department", "科室为空", "请填写所在科室"))
            score -= 20
        if not city:
            issues.append(ValidationIssue("warning", "city", "城市为空", "建议填写所在城市，有助于AI本地化推荐"))
            score -= 10

        # 2. 自我介绍格式检查
        if self_intro:
            # 检查是否包含四要素
            if real_name and real_name not in self_intro:
                issues.append(ValidationIssue("warning", "self_intro_template",
                    f"自我介绍中未包含医生姓名「{real_name}」",
                    "建议在自我介绍中包含真实姓名，格式如「XX市XX医院XX科XX医生」"))
                score -= 10
            if hospital and hospital not in self_intro:
                issues.append(ValidationIssue("warning", "self_intro_template",
                    f"自我介绍中未包含医院名称「{hospital}」",
                    "建议在自我介绍中包含医院全称"))
                score -= 10
            if department and department not in self_intro:
                issues.append(ValidationIssue("warning", "self_intro_template",
                    f"自我介绍中未包含科室「{department}」",
                    "建议在自我介绍中包含科室名称"))
                score -= 5
        else:
            issues.append(ValidationIssue("info", "self_intro_template",
                "未设置自我介绍模板",
                "建议设置统一的自我介绍模板，在所有平台使用相同表述"))
            score -= 5

        # 3. 医院名称规范性检查（是否含"医院"二字）
        if hospital and "医院" not in hospital and "中心" not in hospital and "诊所" not in hospital:
            issues.append(ValidationIssue("warning", "hospital",
                f"医院名称「{hospital}」可能不完整",
                "建议使用医院全称，如「XX市人民医院」"))
            score -= 5

        score = max(0, min(100, score))
        return ValidationResult(score=score, issues=issues)

    def validate_article(self, article, profile) -> ValidationResult:
        """校验文章中的实体一致性

        Args:
            article: ArticleDraft对象
            profile: DoctorProfile对象
        Returns:
            ValidationResult
        """
        issues: List[ValidationIssue] = []
        score = 100

        real_name = (profile.real_name or "").strip()
        hospital = (profile.hospital or "").strip()
        department = (profile.department or "").strip()

        title = (article.title or "").strip()
        content = (article.content or "").strip()
        full_text = f"{title} {content}"

        # 1. 文章是否关联语义
        if not article.semantic_id:
            issues.append(ValidationIssue("warning", "semantic_id",
                "文章未关联语义问题",
                "建议关联语义问题，便于追踪该语义下的内容产出"))
            score -= 10

        # 2. 文章中是否包含医生姓名
        if real_name:
            if real_name not in full_text:
                issues.append(ValidationIssue("warning", "content",
                    f"文章中未提及医生姓名「{real_name}」",
                    "建议在文章署名或正文中包含真实姓名，增强AI实体识别"))
                score -= 15
            else:
                # 检查是否有不一致的署名（如"张医生"vs"张三"）
                # 简单规则：如果有"X医生"格式但X不是real_name的姓，提示
                alias_pattern = r'([\u4e00-\u9fa5]{1,2})医生'
                aliases = re.findall(alias_pattern, full_text)
                for alias in set(aliases):
                    if alias != real_name[:len(alias)] and alias + "医生" != real_name:
                        issues.append(ValidationIssue("info", "content",
                            f"文章中发现署名「{alias}医生」，与真实姓名「{real_name}」可能不一致",
                            f"建议统一使用「{real_name}」或「{real_name[-2:]}医生」作为署名"))
                        score -= 5
                        break

        # 3. 文章中是否包含医院名称
        if hospital and hospital not in full_text:
            issues.append(ValidationIssue("warning", "content",
                f"文章中未提及医院名称「{hospital}」",
                "建议在文章中包含医院全称，增强实体锚定"))
            score -= 10

        # 4. 文章中是否包含科室
        if department and department not in full_text:
            issues.append(ValidationIssue("info", "content",
                f"文章中未提及科室「{department}」",
                "建议在文章中提及科室名称，有助于AI精准关联"))
            score -= 5

        # 5. 文章内容长度检查
        if len(content) < 100:
            issues.append(ValidationIssue("warning", "content",
                f"文章内容较短（{len(content)}字）",
                "建议文章正文不少于300字，内容越丰富AI越容易引用"))
            score -= 10

        score = max(0, min(100, score))
        return ValidationResult(score=score, issues=issues)


# 全局单例
entity_validator = EntityValidator()
