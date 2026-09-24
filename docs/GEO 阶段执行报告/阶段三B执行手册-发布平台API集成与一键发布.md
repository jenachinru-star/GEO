# 阶段三B执行手册：发布平台API集成与一键发布

> 本手册实现微信公众号官方API一键发布，其他平台（知乎/百家号/小红书）留好发布器框架，发布流程全链路打通。

---

## 

- 项目路径：C:\Users\jenac\Desktop\GEO
- 后端路径：C:\Users\jenac\Desktop\GEO\backend
- 前端路径：C:\Users\jenac\Desktop\GEO\frontend
- 技术栈：后端 Python FastAPI + SQLAlchemy + SQLite，前端 React 18 + TypeScript + Ant Design
- 操作系统：Windows
- git 基线：e537de6（工作区必须干净）
- 执行模式：按需确认
- Python 路径：C:\Users\jenac\miniconda3\python.exe（必须用这个）

## 当前发布平台状态（必须理解）

项目已有发布平台的**框架**，但没有**实际发布器**：

| 组件 | 状态 | 位置 |
|------|------|------|
| PublishAccount模型/API | ✅ 完整 | models/publish_account.py, api/publish_account.py |
| publishers/base.py | ✅ 抽象基类 | publishers/base.py |
| publishers/factory.py | ✅ 工厂 | publishers/factory.py |
| publishers/_manual.py | ✅ 半自动兜底 | publishers/_manual.py |
| **实际平台发布器** | ❌ 无 | publishers/目录下只有_manual.py |
| Distribution模型/API | ✅ 完整 | models/distribution.py, api/distribution.py |
| Distribution前端 | ✅ 完整 | pages/Distribution.tsx |

**当前发布流程**：用户手动复制文章内容 → 跳转平台创作页 → 手动粘贴发布 → 回到系统"标记已发布"并回填URL。完全半自动。

## 阶段三B修复总览（8项）

| 编号 | 修复项 | 涉及文件 |
|------|--------|---------|
| E1 | PublishAccount模型加平台特定配置字段 | models/publish_account.py |
| E2 | 微信公众号发布器（官方API） | publishers/wechat.py（新建） |
| E3 | 知乎/百家号/小红书发布器框架（继承ManualPublisher） | publishers/zhihu.py, baijiahao.py, xiaohongshu.py（新建） |
| E4 | 发布器工厂注册所有平台 | publishers/factory.py |
| E5 | 发布执行异步任务（一键发布走AsyncTask） | worker/publish_tasks.py（新建）+ worker.py |
| E6 | Distribution API加"一键发布"接口 | api/distribution.py |
| E7 | Distribution前端加"一键发布"按钮+进度展示 | pages/Distribution.tsx |
| E8 | 发布账号页面前端优化（微信appid/secret分开填） | pages/PublishAccounts.tsx |

## 执行顺序

严格按 E1→E2→...→E8 的顺序执行。每完成一项做一次静态检查。

---

## E1：PublishAccount模型加平台特定配置字段

**根因**：当前PublishAccount的credential字段是一个Text，存cookie/token。但微信公众号需要appid和secret两个字段，分开存储更清晰。

**修复目标**：PublishAccount加 `app_id` 和 `app_secret` 字段（用于微信公众号等需要API密钥的平台），credential字段保留（用于cookie/token类平台）。

**改动**：

**文件**：`backend/app/models/publish_account.py`

```python
# before
class PublishAccount(Base):
    """发布平台账号"""
    __tablename__ = "geo_publish_account"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    account_name = Column(String(200), default="")
    credential = Column(Text, default="")  # cookie 或 access_token
    login_status = Column(String(20), default="unknown")
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# after
class PublishAccount(Base):
    """发布平台账号"""
    __tablename__ = "geo_publish_account"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    account_name = Column(String(200), default="")
    # API密钥类（微信公众号等）
    app_id = Column(String(200), default="")  # 应用ID / AppID
    app_secret = Column(String(500), default="")  # 应用密钥 / AppSecret（加密存储）
    # Cookie/Token类（知乎/百家号等）
    credential = Column(Text, default="")  # cookie 或 access_token（加密存储）
    login_status = Column(String(20), default="unknown")
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**数据库迁移**：在 `database.py` 的 `init_db()` 中加幂等迁移（与现有迁移风格一致）：

```python
# 在 init_db() 的迁移部分加
with engine.connect() as conn:
    cols = [row[1] for row in conn.execute(text("PRAGMA table_info(geo_publish_account)"))]
    if cols:
        if 'app_id' not in cols:
            conn.execute(text("ALTER TABLE geo_publish_account ADD COLUMN app_id VARCHAR(200) DEFAULT ''"))
        if 'app_secret' not in cols:
            conn.execute(text("ALTER TABLE geo_publish_account ADD COLUMN app_secret VARCHAR(500) DEFAULT ''"))
    conn.commit()
```

**注意**：新session先 Read database.py 的 init_db() 确认迁移部分的位置，在合适的地方加。

**验证**：启动后端后，查询 geo_publish_account 表应有 app_id 和 app_secret 字段。

---

## E2：微信公众号发布器（官方API）

**根因**：publishers目录下没有实际的平台发布器，只有_manual.py兜底。

**修复目标**：实现微信公众号官方API发布器，支持：
1. 获取access_token（用appid和secret）
2. 上传图文素材（新增永久图文素材）
3. 发布（群发/发布接口）

**改动**：

**文件**：`backend/app/publishers/wechat.py`（新建）

```python
"""微信公众号发布器 - 官方API

使用微信公众平台官方API发布图文消息。
需要用户在发布账号中配置 AppID 和 AppSecret。

API文档：
- 获取access_token: https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Get_access_token.html
- 新增永久图文素材: https://developers.weixin.qq.com/doc/offiaccount/Asset_Management/Adding_Permanent_Assets.html
- 发布接口: https://developers.weixin.qq.com/doc/offiaccount/Publish/Publish.html
"""
import logging
import requests
from typing import Optional
from app.publishers.base import BasePublisher, PublishResult

logger = logging.getLogger(__name__)

WECHAT_API_BASE = "https://api.weixin.qq.com"


class WechatPublisher(BasePublisher):
    """微信公众号发布器"""

    platform_code = "wechat"
    platform_name = "微信公众号"

    def _get_access_token(self, app_id: str, app_secret: str) -> str:
        """获取access_token"""
        url = f"{WECHAT_API_BASE}/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": app_id,
            "secret": app_secret,
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if "access_token" not in data:
            raise ValueError(f"获取access_token失败: {data}")
        return data["access_token"]

    def _upload_news(self, access_token: str, title: str, content: str,
                      author: str = "", digest: str = "") -> str:
        """新增永久图文素材，返回media_id"""
        url = f"{WECHAT_API_BASE}/cgi-bin/material/add_news"
        params = {"access_token": access_token}

        # 内容简单处理：纯文本直接用，HTML保留
        # 微信图文内容需要是HTML格式
        if not content.startswith("<"):
            # 纯文本转简单HTML
            html_content = content.replace("\n", "<br/>")
        else:
            html_content = content

        article = {
            "title": title,
            "author": author,
            "digest": digest or title[:100],  # 摘要，最多120字
            "content": html_content,
            "content_source_url": "",  # 原文链接
            "thumb_media_id": "",  # 封面图media_id（必填，但这里先留空，实际需要先上传图片）
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }

        payload = {"articles": [article]}
        resp = requests.post(url, params=params, json=payload, timeout=30)
        data = resp.json()
        if "media_id" not in data:
            raise ValueError(f"上传图文素材失败: {data}")
        return data["media_id"]

    def _publish(self, access_token: str, media_id: str) -> str:
        """发布接口，返回publish_id"""
        url = f"{WECHAT_API_BASE}/cgi-bin/freepublish/submit"
        params = {"access_token": access_token}
        payload = {"media_id": media_id}
        resp = requests.post(url, params=params, json=payload, timeout=30)
        data = resp.json()
        if data.get("errcode", 0) != 0:
            raise ValueError(f"发布失败: {data}")
        return data.get("publish_id", "")

    def publish(self, title: str, content: str, account: dict, **kwargs) -> PublishResult:
        """发布文章到微信公众号

        Args:
            title: 文章标题
            content: 文章内容（纯文本或HTML）
            account: 账号信息，需包含 app_id 和 app_secret
            **kwargs: 可选参数，author/digest等

        Returns:
            PublishResult: 发布结果
        """
        try:
            app_id = account.get("app_id", "")
            app_secret = account.get("app_secret", "")

            if not app_id or not app_secret:
                return PublishResult(
                    success=False,
                    platform=self.platform_code,
                    failed_reason="微信公众号未配置AppID和AppSecret，请在发布账号中完善配置",
                )

            author = kwargs.get("author", "")
            digest = kwargs.get("digest", "")

            # 1. 获取access_token
            logger.info("微信公众号发布：获取access_token")
            access_token = self._get_access_token(app_id, app_secret)

            # 2. 上传图文素材
            logger.info(f"微信公众号发布：上传图文素材 title={title[:30]}")
            media_id = self._upload_news(access_token, title, content, author, digest)

            # 3. 发布
            logger.info(f"微信公众号发布：提交发布 media_id={media_id}")
            publish_id = self._publish(access_token, media_id)

            # 微信发布是异步的，publish_id可用于查询状态
            # 这里先返回成功，实际文章URL需要通过发布状态查询获取
            article_url = f"https://mp.weixin.qq.com/s?__biz=placeholder"  # 占位，实际需要查询

            return PublishResult(
                success=True,
                platform=self.platform_code,
                publish_url=article_url,
                publish_id=publish_id,
                message="微信公众号发布成功（发布后可能需要几分钟生效）",
            )

        except Exception as e:
            logger.error(f"微信公众号发布失败: {e}")
            return PublishResult(
                success=False,
                platform=self.platform_code,
                failed_reason=str(e),
            )

    def get_status(self, publish_id: str, account: dict) -> dict:
        """查询发布状态（微信发布是异步的）"""
        try:
            app_id = account.get("app_id", "")
            app_secret = account.get("app_secret", "")
            access_token = self._get_access_token(app_id, app_secret)

            url = f"{WECHAT_API_BASE}/cgi-bin/freepublish/get"
            params = {"access_token": access_token}
            payload = {"publish_id": publish_id}
            resp = requests.post(url, params=params, json=payload, timeout=10)
            data = resp.json()
            return data
        except Exception as e:
            logger.error(f"查询微信发布状态失败: {e}")
            return {"errcode": -1, "errmsg": str(e)}
```

**注意**：
- 微信公众号发布需要封面图（thumb_media_id），上面的代码留空了。实际发布时需要先上传封面图。新session可以先留空（微信会用默认封面），后续优化。
- 微信发布是异步的，提交后需要通过publish_id查询状态和文章URL。上面的代码实现了get_status方法。
- 微信公众号API需要认证的服务号/订阅号才能使用，个人订阅号可能没有发布权限。

**验证**：静态检查import不报错。

---

## E3：知乎/百家号/小红书发布器框架（继承ManualPublisher）

**根因**：这些平台没有官方内容发布API，需要cookie模拟登录，风险高。先继承ManualPublisher留好框架，后续有需求再实现。

**修复目标**：创建zhihu.py、baijiahao.py、xiaohongshu.py三个发布器文件，继承ManualPublisher，标注"待实现"。

**改动**：

**文件1**：`backend/app/publishers/zhihu.py`（新建）

```python
"""知乎发布器 - 待实现

知乎没有官方内容发布API，需要cookie模拟登录。
当前继承ManualPublisher（半自动模式），后续可实现cookie自动发布。
"""
from app.publishers._manual import ManualPublisher


class ZhihuPublisher(ManualPublisher):
    """知乎发布器（当前为半自动模式，待实现自动发布）"""

    platform_code = "zhihu"
    platform_name = "知乎"

    # 后续实现自动发布时，重写 publish() 方法
    # def publish(self, title, content, account, **kwargs):
    #     # 使用account中的cookie调用知乎发布接口
    #     pass
```

**文件2**：`backend/app/publishers/baijiahao.py`（新建）

```python
"""百家号发布器 - 待实现

百家号没有官方内容发布API，需要cookie模拟登录。
当前继承ManualPublisher（半自动模式）。
"""
from app.publishers._manual import ManualPublisher


class BaijiahaoPublisher(ManualPublisher):
    """百家号发布器（当前为半自动模式，待实现自动发布）"""

    platform_code = "baijiahao"
    platform_name = "百家号"
```

**文件3**：`backend/app/publishers/xiaohongshu.py`（新建）

```python
"""小红书发布器 - 待实现

小红书没有官方内容发布API，需要cookie模拟登录。
当前继承ManualPublisher（半自动模式）。
"""
from app.publishers._manual import ManualPublisher


class XiaohongshuPublisher(ManualPublisher):
    """小红书发布器（当前为半自动模式，待实现自动发布）"""

    platform_code = "xiaohongshu"
    platform_name = "小红书"
```

**验证**：静态检查import不报错。

---

## E4：发布器工厂注册所有平台

**根因**：publishers/factory.py的注册表中只有_manual，没有注册实际平台发布器。

**修复目标**：在factory.py中注册wechat/zhihu/baijiahao/xiaohongshu发布器。

**改动**：

**文件**：`backend/app/publishers/factory.py`

新session先 Read 整个文件，确认当前注册表结构，然后修改：

```python
# 在注册表中加
from app.publishers.wechat import WechatPublisher
from app.publishers.zhihu import ZhihuPublisher
from app.publishers.baijiahao import BaijiahaoPublisher
from app.publishers.xiaohongshu import XiaohongshuPublisher

PUBLISHER_REGISTRY = {
    "wechat": WechatPublisher,
    "zhihu": ZhihuPublisher,
    "baijiahao": BaijiahaoPublisher,
    "xiaohongshu": XiaohongshuPublisher,
    # 其他平台回退到 ManualPublisher
}
```

**注意**：新session确认 factory.py 的实际代码结构，可能注册表的变量名和结构不同，按实际结构修改。

**验证**：`publisher_factory.get_publisher("wechat")` 返回 WechatPublisher 实例。

---

## E5：发布执行异步任务（一键发布走AsyncTask）

**根因**：发布到平台可能需要5-30秒（微信API调用），同步阻塞HTTP请求。

**修复目标**：新建 publish_tasks.py，注册 `article_publish` 任务类型，一键发布走AsyncTask异步执行。

**改动**：

**文件1**：`backend/app/worker/publish_tasks.py`（新建）

```python
"""文章发布相关任务的处理函数"""
import json
import logging
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.models.article import ArticleDraft
from app.models.publish_account import PublishAccount
from app.models.distribution import Distribution
from app.publishers.factory import publisher_factory
from app.utils.crypto import decrypt
from app.worker.task_registry import register_handler, ProgressCallback

logger = logging.getLogger(__name__)


def handle_article_publish(db: Session, task: AsyncTask, on_progress: ProgressCallback = None) -> dict:
    """处理文章发布任务"""
    payload = json.loads(task.payload_json or "{}")
    article_id = payload.get("article_id")
    distribution_id = payload.get("distribution_id")
    platform = payload.get("platform")
    user_id = task.created_by

    if not article_id or not platform:
        raise ValueError("payload 中缺少 article_id 或 platform")

    if on_progress:
        on_progress(1, 4, "查询文章和发布账号")

    # 查询文章
    article = db.query(ArticleDraft).filter(
        ArticleDraft.id == article_id, ArticleDraft.user_id == user_id
    ).first()
    if not article:
        raise ValueError("文章不存在或不属于当前用户")

    # 查询发布账号
    account = db.query(PublishAccount).filter(
        PublishAccount.user_id == user_id,
        PublishAccount.platform == platform,
        PublishAccount.login_status == "valid",
    ).first()
    if not account:
        raise ValueError(f"未找到 {platform} 平台的有效发布账号，请先在发布账号中添加并验证")

    # 解密账号信息
    account_dict = {
        "app_id": account.app_id or "",
        "app_secret": decrypt(account.app_secret) if account.app_secret else "",
        "credential": decrypt(account.credential) if account.credential else "",
        "account_name": account.account_name,
    }

    if on_progress:
        on_progress(2, 4, f"调用 {platform} 平台发布API")

    # 获取发布器并执行发布
    publisher = publisher_factory.get_publisher(platform)
    result = publisher.publish(
        title=article.title,
        content=article.content or article.full_text or "",
        account=account_dict,
        author=article.author or "",
    )

    if on_progress:
        on_progress(3, 4, "更新发布记录")

    # 更新distribution记录
    if distribution_id:
        dist = db.query(Distribution).filter(Distribution.id == distribution_id).first()
        if dist:
            if result.success:
                dist.status = "published"
                dist.publish_url = result.publish_url
                dist.published_at = datetime.utcnow()
                dist.note = result.message or "发布成功"
            else:
                dist.status = "failed"
                dist.note = f"发布失败: {result.failed_reason}"
            db.commit()

    if on_progress:
        on_progress(4, 4, "发布完成")

    if not result.success:
        raise ValueError(f"发布失败: {result.failed_reason}")

    return {
        "success": True,
        "platform": platform,
        "publish_url": result.publish_url,
        "publish_id": result.publish_id,
        "message": result.message,
    }


# 注册任务处理函数
register_handler("article_publish", handle_article_publish)
```

**注意**：
- 新session确认 Distribution 模型的字段名（status/publish_url/published_at/note等），如果字段名不同需要调整。
- 新session确认 task_registry 的 register_handler 签名和 ProgressCallback 类型。
- datetime 需要导入。

**文件2**：worker.py 导入 publish_tasks

**文件**：`backend/app/worker/worker.py`

在导入区加：`import app.worker.publish_tasks  # noqa: F401`

**验证**：静态检查import不报错，任务类型注册成功。

---

## E6：Distribution API加"一键发布"接口

**根因**：当前Distribution API只有CRUD和状态更新，没有"一键发布"接口。

**修复目标**：新增 `POST /api/v1/distribution/{dist_id}/publish` 接口，投递 article_publish 异步任务。

**改动**：

**文件**：`backend/app/api/distribution.py`

新session先 Read 整个文件，确认当前接口结构，然后在合适的位置加：

```python
@router.post("/{dist_id}/publish", summary="一键发布到平台")
def publish_to_platform(
    dist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """一键发布文章到指定平台（异步任务）"""
    from app.models.task import AsyncTask
    from app.models.distribution import Distribution
    import json

    dist = db.query(Distribution).filter(
        Distribution.id == dist_id, Distribution.user_id == user_id
    ).first()
    if not dist:
        raise HTTPException(status_code=404, detail="发布记录不存在")

    if dist.status == "published":
        raise HTTPException(status_code=400, detail="该文章已发布")

    if dist.status in ("processing", "scheduled"):
        raise HTTPException(status_code=400, detail="该文章正在发布中")

    # 更新状态为processing
    dist.status = "processing"
    dist.note = "一键发布任务已提交，等待执行"
    db.commit()

    # 投递异步任务
    task = AsyncTask(
        task_type="article_publish",
        status="queued",
        created_by=user_id,
        payload_json=json.dumps({
            "article_id": dist.article_id,
            "distribution_id": dist.id,
            "platform": dist.platform,
        }, ensure_ascii=False),
        progress_message="等待执行",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "code": 0,
        "message": "发布任务已提交",
        "data": {
            "task_id": task.id,
            "distribution_id": dist.id,
            "platform": dist.platform,
            "status": "queued",
        }
    }
```

**注意**：
- 新session确认 Distribution 模型的字段名（user_id/article_id/platform等），如果字段名不同需要调整。
- 新session确认 distribution.py 的路由前缀和导入。

**验证**：调用一键发布接口，返回task_id，任务中心显示article_publish任务。

---

## E7：Distribution前端加"一键发布"按钮+进度展示

**根因**：当前Distribution前端只有"标记已发布"（手动），没有"一键发布"按钮。

**修复目标**：Distribution页面加"一键发布"按钮，点击后调用发布接口，轮询任务进度，显示发布结果。

**改动**：

**文件**：`frontend/src/pages/Distribution.tsx`

新session先 Read 整个文件，确认当前表格操作列的结构，然后修改：

1. **操作列加"一键发布"按钮**（在draft/scheduled状态时显示）：

```tsx
// 在操作列的render中加
{record.status === 'draft' || record.status === 'scheduled' ? (
  <Button
    key="auto-publish"
    size="small"
    type="primary"
    icon={<SendOutlined />}
    loading={publishingId === record.id}
    onClick={() => handleAutoPublish(record)}
  >
    一键发布
  </Button>
) : null}
```

2. **handleAutoPublish 函数**：

```tsx
const [publishingId, setPublishingId] = useState<number | null>(null)
const [publishPollTimer, setPublishPollTimer] = useState<number | null>(null)

const handleAutoPublish = async (record: any) => {
  try {
    setPublishingId(record.id)
    const res: any = await request.post(`/distribution/${record.id}/publish`)
    const taskId = res.data?.task_id
    message.success('发布任务已提交，正在发布中...')

    // 轮询任务状态
    if (publishPollTimer) clearInterval(publishPollTimer)
    const timer = window.setInterval(async () => {
      try {
        const taskRes: any = await request.get(`/task/${taskId}`)
        const status = taskRes.data?.status
        if (status === 'succeeded') {
          clearInterval(timer)
          setPublishPollTimer(null)
          setPublishingId(null)
          message.success('发布成功！')
          fetchData()
        } else if (status === 'failed') {
          clearInterval(timer)
          setPublishPollTimer(null)
          setPublishingId(null)
          message.error(taskRes.data?.error_message || '发布失败')
          fetchData()
        }
      } catch (e) {
        // 轮询错误静默
      }
    }, 3000)
    setPublishPollTimer(timer)
  } catch (e) {
    setPublishingId(null)
    // 错误提示已由拦截器统一弹出
  }
}

// 组件卸载时清除定时器
useEffect(() => {
  return () => {
    if (publishPollTimer) clearInterval(publishPollTimer)
  }
}, [])
```

3. **processing状态显示进度**：在状态列加"发布中..."的loading提示。

**注意**：
- 新session确认 Distribution.tsx 的实际代码结构，按实际结构修改。
- 新session确认 api/index.ts 中是否有 distributionApi，如果有就用 distributionApi.publish，如果没有就用 request.post。
- SendOutlined 图标需要从 @ant-design/icons 导入。

**验证**：点击"一键发布"，按钮显示loading，任务中心显示发布任务，发布成功后状态变为"已发布"。

---

## E8：发布账号页面前端优化（微信appid/secret分开填）

**根因**：当前PublishAccounts页面的添加账号表单只有一个credential字段（TextArea），微信公众号需要appid和secret两个字段，用户不知道怎么填。

**修复目标**：根据选择的平台动态显示不同的表单字段：
- 微信公众号：显示 AppID（Input）+ AppSecret（Input.Password）+ 账号名称
- 知乎/百家号/小红书：显示 Cookie/Token（TextArea）+ 账号名称

**改动**：

**文件**：`frontend/src/pages/PublishAccounts.tsx`

新session先 Read 整个文件（约200行），确认当前表单结构，然后修改：

1. **表单根据平台动态显示字段**：

```tsx
const [selectedPlatform, setSelectedPlatform] = useState('')

// 在表单中
<Form.Item name="platform" label="发布平台" rules={[{ required: true }]}>
  <Select
    placeholder="选择发布平台"
    onChange={(value) => setSelectedPlatform(value)}
    showSearch
    optionFilterProp="label"
  >
    <Option value="wechat" label="微信公众号">微信公众号（官方API）</Option>
    <Option value="zhihu" label="知乎">知乎（半自动）</Option>
    <Option value="baijiahao" label="百家号">百家号（半自动）</Option>
    <Option value="xiaohongshu" label="小红书">小红书（半自动）</Option>
  </Select>
</Form.Item>

<Form.Item name="account_name" label="账号名称">
  <Input placeholder="账号昵称/展示名" />
</Form.Item>

{/* 微信公众号：显示 AppID + AppSecret */}
{selectedPlatform === 'wechat' && (
  <>
    <Form.Item name="app_id" label="AppID" rules={[{ required: true, message: '请填写AppID' }]}>
      <Input placeholder="微信公众号的AppID" />
    </Form.Item>
    <Form.Item name="app_secret" label="AppSecret" rules={[{ required: true, message: '请填写AppSecret' }]}>
      <Input.Password placeholder="微信公众号的AppSecret" />
    </Form.Item>
  </>
)}

{/* 其他平台：显示 Cookie/Token */}
{selectedPlatform && selectedPlatform !== 'wechat' && (
  <Form.Item name="credential" label="Cookie/Token">
    <TextArea rows={4} placeholder="粘贴登录后的Cookie或Access Token" />
  </Form.Item>
)}

<Form.Item name="note" label="备注">
  <Input placeholder="可选备注" />
</Form.Item>
```

2. **后端API配合**：`api/publish_account.py` 的 AccountCreate 已经有 credential 字段，需要加 app_id 和 app_secret 字段。新session确认 AccountCreate 的定义，加上这两个字段。

3. **创建账号时加密 app_secret**：后端 create_account 中，app_secret 也需要加密存储（和credential一样）。

**注意**：
- 新session确认 PublishAccounts.tsx 的实际表单结构，按实际结构修改。
- 后端 AccountCreate 需要加 app_id 和 app_secret 字段。
- 后端 create_account 需要加密 app_secret。
- 编辑账号时，app_secret 字段留空表示不修改（和API Key的处理方式一致）。

**验证**：选择微信公众号时显示AppID+AppSecret字段，选择其他平台时显示Cookie字段。

---

## 全部完成后的统一验证

8项全部修改完成后，按以下步骤统一验证：

### 1. 后端静态检查
```bash
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\miniconda3\python.exe -c "from app.main import app; print('import OK')"
```

### 2. 前端静态检查
```bash
cd C:\Users\jenac\Desktop\GEO\frontend
npx tsc --noEmit
```

### 3. 启动后端
确认无ERROR，任务类型注册包含 article_publish。

### 4. 功能验证清单

| 验证项 | 操作 | 预期 |
|--------|------|------|
| E1 数据库字段 | 启动后端后查表 | geo_publish_account有app_id/app_secret字段 |
| E2 微信发布器 | 静态检查 | WechatPublisher类存在，方法完整 |
| E3 其他平台框架 | 静态检查 | zhihu/baijiahao/xiaohongshu发布器存在 |
| E4 工厂注册 | 调用publisher_factory.get_publisher('wechat') | 返回WechatPublisher实例 |
| E5 异步任务 | 任务类型列表 | 包含article_publish |
| E6 一键发布API | 调用POST /distribution/{id}/publish | 返回task_id |
| E7 前端一键发布 | Distribution页面点击一键发布 | 按钮loading，任务执行，状态更新 |
| E8 账号表单 | 添加账号选择微信公众号 | 显示AppID+AppSecret字段 |

### 5. git 提交
```bash
cd C:\Users\jenac\Desktop\GEO
git add -A
git commit -m "feat: 阶段三B-发布平台API集成与一键发布（8项）"
```

---

## 注意事项

1. **微信公众号发布需要真实的AppID和AppSecret**：测试时需要用户提供有效的微信公众号凭证。如果没有，可以先验证框架（发布器创建、任务投递、前端按钮），实际发布留到用户有凭证后验证。
2. **微信发布是异步的**：提交发布后需要通过publish_id查询状态和文章URL。当前实现先返回成功，文章URL是占位。后续可以优化为轮询查询真实URL。
3. **封面图问题**：微信图文发布需要封面图（thumb_media_id），当前留空。微信会用默认封面，但可能不符合预期。后续可以加封面图上传功能。
4. **其他平台（知乎/百家号/小红书）**：当前继承ManualPublisher（半自动），没有实现自动发布。因为这些平台没有官方API，需要cookie模拟登录，风险高。后续有需求再实现。
5. **E7前端改动较大**：新session必须先 Read Distribution.tsx 确认实际代码结构，按实际结构修改，不要凭记忆写。
6. **E8后端需要配合**：AccountCreate加app_id/app_secret字段，create_account加密app_secret。新session确认后端代码后修改。
7. **每完成一项做一次静态检查**。

## 最终输出

完成后输出报告：
1. 8项修复的状态（✅/⚠️/❌）
2. 每项实际改动的文件和行号
3. 新建的文件列表
4. 验证结果
5. git commit hash
6. 遇到的问题和未完成项（如果有）

---

现在开始：第一步，用 Read 工具读取所有涉及的文件，确认当前代码状态。
