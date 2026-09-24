# -*- coding: utf-8 -*-
"""微信公众号数据采集异步任务
payload:
- 窗口模式：{"account_id": int, "days": int}
- 指定群发日模式（定时任务）：{"account_id": int, "dates": ["YYYY-MM-DD", ...]}
"""
import json
import logging
from datetime import date
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.models.publish_account import PublishAccount
from app.services.wechat_data_service import WechatDataService
from app.worker.task_registry import register_handler

logger = logging.getLogger(__name__)


def handle_wechat_data_collect(db: Session, task: AsyncTask, on_progress) -> dict:
    """处理微信公众号数据采集任务"""
    payload = json.loads(task.payload_json or "{}")
    account_id = payload.get("account_id")
    days = payload.get("days", 7)
    date_strings = payload.get("dates")

    if not account_id:
        raise ValueError("缺少account_id参数")

    account = db.query(PublishAccount).filter(PublishAccount.id == account_id).first()
    if not account:
        raise ValueError(f"账号不存在: {account_id}")

    ref_dates = None
    if date_strings:
        ref_dates = []
        for s in date_strings:
            try:
                ref_dates.append(date.fromisoformat(s))
            except ValueError:
                logger.warning(f"忽略无法解析的日期: {s}")
        if not ref_dates:
            raise ValueError("payload dates 中没有有效日期")

    mode_desc = f"指定{len(ref_dates)}个群发日" if ref_dates else f"最近{days}天"
    on_progress(1, 3, f"开始采集账号 [{account.account_name}] 数据（{mode_desc}）")

    result = WechatDataService.collect_and_store(
        db, account, days=days, ref_dates=ref_dates
    )

    on_progress(3, 3, f"采集完成: 账号统计{result['account_stats_count']}天, "
                      f"文章新增{result['article_count']}篇, 文章快照{result['article_stats_count']}条")

    return result


# 注册任务处理函数
register_handler("wechat_data_collect", handle_wechat_data_collect)
