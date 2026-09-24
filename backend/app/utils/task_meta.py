# -*- coding: utf-8 -*-
"""任务类型元信息：中文名称、描述、图标等
所有任务类型的中文名统一在此维护，前端零维护。
"""

TASK_TYPE_META = {
    "geo_refresh": {
        "name": "GEO全量采集",
        "description": "全量采集所有语义问题在各平台的搜索结果",
    },
    "monitor_collect": {
        "name": "品牌监测采集",
        "description": "监测品牌关键词在各平台的提及情况",
    },
    "asset_url_collect": {
        "name": "资产URL采集",
        "description": "采集URL链接的正文内容并解析为数字资产",
    },
    "asset_file_parse": {
        "name": "资产文件解析",
        "description": "解析上传的文件（PDF/Word等）为数字资产",
    },
    "article_generate": {
        "name": "文章生成",
        "description": "基于内容机会和医生资料生成科普文章",
    },
    "compliance_check": {
        "name": "合规检查",
        "description": "检查文章内容是否符合医疗合规要求",
    },
    "image_generate": {
        "name": "图片生成",
        "description": "AI生成文章配图或封面图",
    },
    "wechat_data_collect": {
        "name": "微信数据采集",
        "description": "采集微信公众号文章阅读/点赞/分享等数据",
    },
    "article_analysis": {
        "name": "文章AI分析",
        "description": "AI分析文章标题/内容/互动/选题优化建议",
    },
    "semantic_generate": {
        "name": "语义问题生成",
        "description": "基于医生资料自动生成关联语义问题",
    },
    "article_publish": {
        "name": "文章发布",
        "description": "将文章发布到微信公众号等平台",
    },
    "asset_export": {
        "name": "资产导出",
        "description": "导出数字资产为Excel/PDF等格式",
    },
}


def get_task_type_name(task_type: str) -> str:
    """获取任务类型中文名，未知类型返回原类型名"""
    meta = TASK_TYPE_META.get(task_type)
    return meta["name"] if meta else task_type


def get_task_type_meta(task_type: str) -> dict:
    """获取任务类型完整元信息"""
    return TASK_TYPE_META.get(task_type, {"name": task_type, "description": ""})


def get_all_task_types() -> list:
    """获取所有任务类型列表（含中文名）"""
    return [
        {"type": k, "name": v["name"], "description": v["description"]}
        for k, v in TASK_TYPE_META.items()
    ]
