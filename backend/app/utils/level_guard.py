"""知识库访问级别防护工具

级别定义：
- public: 公开级，所有用户可访问
- internal: 内部级，登录用户可访问
- confidential: 机密级，仅admin可访问
"""

# 级别层级（数字越大越敏感）
LEVEL_ORDER = {"public": 0, "internal": 1, "confidential": 2}

# 普通用户可访问的最高级别
DEFAULT_MAX_LEVEL = "internal"
# admin可访问的最高级别
ADMIN_MAX_LEVEL = "confidential"


def get_effective_level(requested_level: str, is_admin: bool = False) -> str:
    """根据用户角色计算实际可访问的级别

    Args:
        requested_level: 前端请求的级别
        is_admin: 是否管理员

    Returns:
        实际生效的级别（不超过用户权限上限）
    """
    max_level = ADMIN_MAX_LEVEL if is_admin else DEFAULT_MAX_LEVEL
    max_order = LEVEL_ORDER.get(max_level, 1)
    requested_order = LEVEL_ORDER.get(requested_level, 0)

    # 如果请求的级别超过用户权限，降级到用户可访问的最高级别
    if requested_order > max_order:
        return max_level
    return requested_level
