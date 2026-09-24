# 阶段二A执行手册：核心架构修复与异步化改造

本手册包含9项修复，按顺序执行。每项都有完整的before/after代码和验证步骤。

## 项目信息

- 项目路径：C:\Users\jenac\Desktop\GEO
- 技术栈：后端 Python FastAPI + SQLAlchemy + SQLite，前端 React 18 + TypeScript + Ant Design
- 操作系统：Windows
- git 基线：最新commit（工作区必须干净）
- 执行模式：按需确认，命令行操作会弹窗确认
- Python 路径：C:\Users\jenac\miniconda3\python.exe（必须用这个，系统PATH中的python缺依赖）

## 9项修复总览

| 编号 | 修复项 | 严重度 | 改动文件 |
|------|--------|--------|---------|
| 2.1 | 用户停用平台后collector仍调用 | P1 | collector.py |
| 2.2 | 采集4平台串行→并发 | P1 | collector.py |
| 2.3 | Worker全局FIFO→按用户轮询 | P1 | worker.py |
| 2.4 | 任务编号全局自增→用户级序号 | P2 | task.py + TaskCenter.tsx |
| 2.5 | minimax单独配置超时 | P2 | config.py + openai_compatible.py + factory.py |
| 2.6 | 文章生成同步阻塞→异步任务 | P1 | template.py + 新建article_tasks.py + task_registry |
| 2.7 | 合规检查同步阻塞→异步任务 | P1 | compliance.py + 新建compliance_tasks.py |
| 2.8 | 生图同步阻塞→异步任务 | P1 | image.py + 新建image_tasks.py |
| 2.9 | 定时采集不走队列→投递AsyncTask | P1 | main.py |

## 执行顺序

严格按 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6 → 2.7 → 2.8 → 2.9 的顺序执行。每完成一项做一次静态检查（import不报错），全部完成后统一启动验证。

---

## 修复2.1：用户停用平台后collector仍调用

### 根因

`collector.py` 的 `collect_one_semantic()` 和 `collect_one_question()` 中，`adapter_factory.get_enabled_platforms()` 只从 `.env` 读取已配置平台，**完全不查用户级平台开关（UserPlatformPref表）**。用户在前端停用 deepseek 后，collector 仍然尝试调用，只是被配额检查拦截后触发熔断。

### 修复目标

采集前查询用户的 UserPlatformPref，过滤掉用户停用的平台，从源头跳过，不浪费调用。

### 改动1：collect_one_semantic 加用户平台过滤

**文件**：`backend/app/engines/collector.py`

**位置**：第 143-159 行（`collect_one_semantic` 方法开头）

```python
# before
    def collect_one_semantic(self, semantic, profile, detect_round: int = 99) -> List[MonitorRecord]:
        """采集单个语义在所有平台的GEO/AEO数据（医生维度）

        Args:
            semantic: Semantic模型对象
            profile: DoctorProfile模型对象
            detect_round: 采集轮次，医生维度固定用99
        """
        from app.engines.geo_aeo_analyzer import GEOAEOAnalyzer

        records = []
        today = datetime.now().strftime("%Y-%m-%d")
        platforms = adapter_factory.get_enabled_platforms()

        if not platforms:
            logger.warning("没有已启用的平台")
            return records

# after
    def collect_one_semantic(self, semantic, profile, detect_round: int = 99, user_id: int = None) -> List[MonitorRecord]:
        """采集单个语义在所有平台的GEO/AEO数据（医生维度）

        Args:
            semantic: Semantic模型对象
            profile: DoctorProfile模型对象
            detect_round: 采集轮次，医生维度固定用99
            user_id: 用户ID，用于过滤用户停用的平台
        """
        from app.engines.geo_aeo_analyzer import GEOAEOAnalyzer
        from app.models.user_platform_pref import UserPlatformPref

        records = []
        today = datetime.now().strftime("%Y-%m-%d")
        platforms = adapter_factory.get_enabled_platforms()

        # 过滤用户停用的平台
        if user_id:
            disabled = {
                pref.platform_code for pref in
                self.db.query(UserPlatformPref).filter(
                    UserPlatformPref.user_id == user_id,
                    UserPlatformPref.enabled == False
                ).all()
            }
            if disabled:
                logger.info(f"用户 [{user_id}] 已停用平台: {disabled}，采集时跳过")
                platforms = [p for p in platforms if p not in disabled]

        if not platforms:
            logger.warning("没有已启用的平台")
            return records
```

### 改动2：collect_one_question 加用户平台过滤

**文件**：`backend/app/engines/collector.py`

**位置**：第 61-69 行（`collect_one_question` 方法开头）

```python
# before
    def collect_one_question(self, question: Question, detect_round: int = 1) -> List[MonitorRecord]:
        """采集单个问题在所有平台的回答（串行模式）"""
        records = []
        today = datetime.now().strftime("%Y-%m-%d")
        platforms = adapter_factory.get_enabled_platforms()

        if not platforms:
            logger.warning("没有已启用的平台")
            return records

# after
    def collect_one_question(self, question: Question, detect_round: int = 1, user_id: int = None) -> List[MonitorRecord]:
        """采集单个问题在所有平台的回答（串行模式）"""
        from app.models.user_platform_pref import UserPlatformPref

        records = []
        today = datetime.now().strftime("%Y-%m-%d")
        platforms = adapter_factory.get_enabled_platforms()

        # 过滤用户停用的平台
        if user_id:
            disabled = {
                pref.platform_code for pref in
                self.db.query(UserPlatformPref).filter(
                    UserPlatformPref.user_id == user_id,
                    UserPlatformPref.enabled == False
                ).all()
            }
            if disabled:
                logger.info(f"用户 [{user_id}] 已停用平台: {disabled}，采集时跳过")
                platforms = [p for p in platforms if p not in disabled]

        if not platforms:
            logger.warning("没有已启用的平台")
            return records
```

### 改动3：collect_all_semantics 传入 user_id

**文件**：`backend/app/engines/collector.py`

**位置**：第 294-296 行（`collect_all_semantics` 中调用 collect_one_semantic）

```python
# before
        for i, semantic in enumerate(semantics):
            try:
                records = self.collect_one_semantic(semantic, profile, detect_round)

# after
        for i, semantic in enumerate(semantics):
            try:
                records = self.collect_one_semantic(semantic, profile, detect_round, user_id=user_id)
```

### 验证

- 静态检查：`C:\Users\jenac\miniconda3\python.exe -c "from app.engines.collector import CollectorEngine; print('OK')"`
- 运行时验证（后续统一做）：用户停用 deepseek 后触发采集，日志应显示"用户 [5] 已停用平台: {'deepseek'}，采集时跳过"，不再出现 deepseek 的调用请求

---

## 修复2.2：采集4平台串行→并发

### 根因

`collect_one_semantic()` 中 `for platform_code in platforms:` 是纯串行循环，4个平台一个接一个调用，每个平台间还有 `time.sleep(1)`。单语义采集时间约113秒，19个语义约36分钟。

### 修复目标

用 `concurrent.futures.ThreadPoolExecutor` 并发调用4个平台，单语义采集时间降到约40秒（最慢的平台），总采集时间提升约3倍。

### 改动1：collect_one_semantic 改为并发

**文件**：`backend/app/engines/collector.py`

**位置**：第 169-256 行（`collect_one_semantic` 中的平台循环部分）

这是最大的一处改动。把整个 `for platform_code in platforms:` 循环替换为并发执行。

```python
# before（第169-256行，整个平台循环）
        logger.info(f"开始GEO/AEO采集语义 [{semantic.id}]: {semantic.question}")

        for platform_code in platforms:
            logger.info(f"  -> 采集平台: {platform_code}")
            success, answer = self.query_single_platform(platform_code, semantic.question)

            if success and answer:
                result = analyzer.analyze(answer)
                logger.info(f"  -> {platform_code}: GEO={'是' if result.geo_mentioned else '否'}(排名{result.geo_rank}), AEO={'是' if result.aeo_cited else '否'}")

                # 提取提及证据片段
                mention_evidence = ""
                if result.geo_mentioned:
                    for pattern in analyzer.patterns:
                        m = pattern.search(answer)
                        if m:
                            start = max(0, m.start() - 100)
                            end = min(len(answer), m.end() + 100)
                            mention_evidence = answer[start:end].strip()
                            break

                # LLM辅助分析
                is_recommendation = False
                recommendation_evidence = ""
                citation_urls = []
                sentiment_score = 0.0
                if result.geo_mentioned:
                    try:
                        llm_result = llm_analyzer.analyze(
                            answer, profile.real_name, profile.hospital, profile.department
                        )
                        is_recommendation = llm_result.is_recommendation
                        recommendation_evidence = llm_result.recommendation_evidence
                        citation_urls = llm_result.citation_urls
                        sentiment_map = {"positive": 0.5, "neutral": 0.0, "negative": -0.5, "mixed": 0.2}
                        sentiment_score = sentiment_map.get(llm_result.sentiment, 0.0)
                    except Exception as e:
                        logger.warning(f"LLM分析失败，降级: {e}")

                aeo_cited = result.aeo_cited and len(citation_urls) > 0
                aeo_confidence = result.aeo_confidence if aeo_cited else (result.aeo_confidence * 0.3 if result.aeo_cited else 0.0)

                record = MonitorRecord(
                    question_id=semantic.id,
                    semantic_id=semantic.id,
                    platform_code=platform_code,
                    rank=result.geo_rank if result.geo_rank else 0,
                    mentioned=result.geo_mentioned,
                    sentiment=sentiment_score,
                    raw_answer=answer,
                    detect_date=today,
                    detect_round=detect_round,
                    detect_type="doctor",
                    recommend_count=1 if is_recommendation else 0,
                    cite_count=1 if aeo_cited else 0,
                    aeo_confidence=aeo_confidence,
                    mention_evidence=mention_evidence,
                    recommendation_evidence=recommendation_evidence,
                    citation_urls=json.dumps(citation_urls, ensure_ascii=False),
                    analyzer_version="rule_v2+llm_v1",
                    raw_sources_json="[]",
                    is_recommendation=1 if is_recommendation else 0,
                )
            else:
                logger.error(f"  -> {platform_code} 采集失败: {answer[:100]}")
                record = MonitorRecord(
                    question_id=semantic.id,
                    semantic_id=semantic.id,
                    platform_code=platform_code,
                    rank=0,
                    mentioned=False,
                    sentiment=0.0,
                    raw_answer=f"采集失败: {answer[:500]}",
                    detect_date=today,
                    detect_round=detect_round,
                    detect_type="doctor",
                    recommend_count=0,
                    cite_count=0,
                    aeo_confidence=0.0,
                )

            records.append(record)
            time.sleep(1)

# after（替换为并发执行）
        logger.info(f"开始GEO/AEO采集语义 [{semantic.id}]: {semantic.question}（并发模式，{len(platforms)}个平台）")

        # 并发调用所有平台
        from concurrent.futures import ThreadPoolExecutor, as_completed
        platform_results = {}  # platform_code -> (success, answer)

        def _collect_platform(platform_code: str):
            logger.info(f"  -> 采集平台: {platform_code}")
            success, answer = self.query_single_platform(platform_code, semantic.question)
            return platform_code, success, answer

        with ThreadPoolExecutor(max_workers=len(platforms)) as executor:
            futures = [executor.submit(_collect_platform, code) for code in platforms]
            for future in as_completed(futures):
                try:
                    platform_code, success, answer = future.result()
                    platform_results[platform_code] = (success, answer)
                except Exception as e:
                    logger.error(f"平台采集异常: {e}")

        # 按平台顺序处理结果（保持记录顺序一致）
        for platform_code in platforms:
            success, answer = platform_results.get(platform_code, (False, "采集异常"))

            if success and answer:
                result = analyzer.analyze(answer)
                logger.info(f"  -> {platform_code}: GEO={'是' if result.geo_mentioned else '否'}(排名{result.geo_rank}), AEO={'是' if result.aeo_cited else '否'}")

                mention_evidence = ""
                if result.geo_mentioned:
                    for pattern in analyzer.patterns:
                        m = pattern.search(answer)
                        if m:
                            start = max(0, m.start() - 100)
                            end = min(len(answer), m.end() + 100)
                            mention_evidence = answer[start:end].strip()
                            break

                is_recommendation = False
                recommendation_evidence = ""
                citation_urls = []
                sentiment_score = 0.0
                if result.geo_mentioned:
                    try:
                        llm_result = llm_analyzer.analyze(
                            answer, profile.real_name, profile.hospital, profile.department
                        )
                        is_recommendation = llm_result.is_recommendation
                        recommendation_evidence = llm_result.recommendation_evidence
                        citation_urls = llm_result.citation_urls
                        sentiment_map = {"positive": 0.5, "neutral": 0.0, "negative": -0.5, "mixed": 0.2}
                        sentiment_score = sentiment_map.get(llm_result.sentiment, 0.0)
                    except Exception as e:
                        logger.warning(f"LLM分析失败，降级: {e}")

                aeo_cited = result.aeo_cited and len(citation_urls) > 0
                aeo_confidence = result.aeo_confidence if aeo_cited else (result.aeo_confidence * 0.3 if result.aeo_cited else 0.0)

                record = MonitorRecord(
                    question_id=semantic.id,
                    semantic_id=semantic.id,
                    platform_code=platform_code,
                    rank=result.geo_rank if result.geo_rank else 0,
                    mentioned=result.geo_mentioned,
                    sentiment=sentiment_score,
                    raw_answer=answer,
                    detect_date=today,
                    detect_round=detect_round,
                    detect_type="doctor",
                    recommend_count=1 if is_recommendation else 0,
                    cite_count=1 if aeo_cited else 0,
                    aeo_confidence=aeo_confidence,
                    mention_evidence=mention_evidence,
                    recommendation_evidence=recommendation_evidence,
                    citation_urls=json.dumps(citation_urls, ensure_ascii=False),
                    analyzer_version="rule_v2+llm_v1",
                    raw_sources_json="[]",
                    is_recommendation=1 if is_recommendation else 0,
                )
            else:
                logger.error(f"  -> {platform_code} 采集失败: {answer[:100]}")
                record = MonitorRecord(
                    question_id=semantic.id,
                    semantic_id=semantic.id,
                    platform_code=platform_code,
                    rank=0,
                    mentioned=False,
                    sentiment=0.0,
                    raw_answer=f"采集失败: {answer[:500]}",
                    detect_date=today,
                    detect_round=detect_round,
                    detect_type="doctor",
                    recommend_count=0,
                    cite_count=0,
                    aeo_confidence=0.0,
                )

            records.append(record)
```

**注意**：
- 并发调用后，LLM分析（`llm_analyzer.analyze`）仍然是串行的，因为它是CPU密集型且可能有线程安全问题。只有平台API调用是并发的。
- 移除了平台间的 `time.sleep(1)`，因为并发不需要间隔。
- 结果处理按 `platforms` 列表顺序，保证记录顺序一致。

### 验证

- 静态检查：`C:\Users\jenac\miniconda3\python.exe -c "from app.engines.collector import CollectorEngine; print('OK')"`
- 运行时验证：触发采集，日志应显示"并发模式，4个平台"，4个平台的请求几乎同时发出，单语义采集时间从~113秒降到~40秒

---

## 修复2.3：Worker全局FIFO→按用户轮询

### 根因

`claim_next_task()` 按 `created_at.asc()` 全局FIFO认领任务。用户A发起10个任务后，用户B的任务要等用户A的任务全部执行完才能开始。

### 修复目标

Worker认领任务时，记住"上一次执行的用户"，这次优先认领其他用户的任务，实现按用户轮询。

### 改动

**文件**：`backend/app/worker/worker.py`

**位置**：第 40-43 行（全局变量区）+ 第 93-132 行（claim_next_task函数）

```python
# before（第40-43行）
# 全局运行标志
_running = True
TASK_TIMEOUT_SECONDS = 600  # 任务超时时间
POLL_INTERVAL = 3  # 轮询间隔（秒）

# after
# 全局运行标志
_running = True
TASK_TIMEOUT_SECONDS = 600  # 任务超时时间
POLL_INTERVAL = 3  # 轮询间隔（秒）
_last_executed_user = None  # 上一次执行任务的用户ID，用于轮询调度
```

```python
# before（第93-132行，整个claim_next_task函数）
def claim_next_task(db: Session) -> AsyncTask | None:
    """认领下一个 queued 任务（原子UPDATE，多线程安全）"""
    # 先查候选任务
    task = db.query(AsyncTask).filter(
        AsyncTask.status == "queued"
    ).order_by(AsyncTask.created_at.asc()).first()

    if not task:
        return None

    # 用原子UPDATE认领：只有status仍是queued时才更新成功
    from sqlalchemy import update as sa_update
    result = db.execute(
        sa_update(AsyncTask)
        .where(AsyncTask.id == task.id, AsyncTask.status == "queued")
        .values(
            status="running",
            started_at=datetime.now(),
            progress_message="任务开始执行",
        )
    )
    db.commit()

    if result.rowcount == 0:
        # 被其他线程认领了
        return None

    db.refresh(task)

    # 排队超时检查：任务在队列中等待过久（超过该任务类型超时的2倍），直接标记failed不执行
    queue_timeout = get_task_timeout(task.task_type) * 2
    if task.created_at and (datetime.utcnow() - task.created_at).total_seconds() > queue_timeout:
        logger.warning(f"任务 #{task.id} 排队超时（created_at={task.created_at}, 阈值={queue_timeout}s），标记为failed")
        task.status = "failed"
        task.error_message = "任务排队超时"
        task.finished_at = datetime.utcnow()
        db.commit()
        return None

    logger.info(f"认领任务 #{task.id} (type={task.task_type})")
    return task

# after
def claim_next_task(db: Session) -> AsyncTask | None:
    """认领下一个 queued 任务（按用户轮询调度，多线程安全）"""
    global _last_executed_user

    # 先查所有 queued 任务，按创建时间排序
    queued_tasks = db.query(AsyncTask).filter(
        AsyncTask.status == "queued"
    ).order_by(AsyncTask.created_at.asc()).all()

    if not queued_tasks:
        return None

    # 按用户轮询：优先选择与上一次执行用户不同的任务
    selected_task = None
    if _last_executed_user is not None:
        # 找第一个不是上一次用户的任务
        for t in queued_tasks:
            if t.created_by != _last_executed_user:
                selected_task = t
                break
    # 如果所有任务都是上一次用户的，或者没有上一次用户记录，选最早的
    if selected_task is None:
        selected_task = queued_tasks[0]

    # 用原子UPDATE认领：只有status仍是queued时才更新成功
    from sqlalchemy import update as sa_update
    result = db.execute(
        sa_update(AsyncTask)
        .where(AsyncTask.id == selected_task.id, AsyncTask.status == "queued")
        .values(
            status="running",
            started_at=datetime.now(),
            progress_message="任务开始执行",
        )
    )
    db.commit()

    if result.rowcount == 0:
        # 被其他线程认领了，尝试下一个
        return None

    db.refresh(selected_task)

    # 记录上一次执行的用户，用于轮询
    _last_executed_user = selected_task.created_by

    # 排队超时检查
    queue_timeout = get_task_timeout(selected_task.task_type) * 2
    if selected_task.created_at and (datetime.utcnow() - selected_task.created_at).total_seconds() > queue_timeout:
        logger.warning(f"任务 #{selected_task.id} 排队超时（created_at={selected_task.created_at}, 阈值={queue_timeout}s），标记为failed")
        selected_task.status = "failed"
        selected_task.error_message = "任务排队超时"
        selected_task.finished_at = datetime.utcnow()
        db.commit()
        return None

    logger.info(f"认领任务 #{selected_task.id} (type={selected_task.task_type}, user={selected_task.created_by})")
    return selected_task
```

### 验证

- 静态检查：`C:\Users\jenac\miniconda3\python.exe -c "from app.worker.worker import claim_next_task; print('OK')"`
- 运行时验证：用户A发起多个任务后用户B发起任务，日志应显示用户B的任务被优先认领（不等待用户A的全部任务完成）

---

## 修复2.4：任务编号全局自增→用户级序号

### 根因

AsyncTask的id是数据库全局自增主键，用户看到"任务#21"但实际是自己的第4个任务，体验差。

### 修复目标

API返回时加 `user_seq` 字段（该用户的第几个任务），前端显示"我的任务#N"。数据库id保持全局不变。

### 改动1：list_tasks 返回加 user_seq

**文件**：`backend/app/api/task.py`

**位置**：第 64-83 行（list_tasks的返回部分）

```python
# before
    total = query.count()
    items = query.order_by(AsyncTask.created_at.desc())\
        .offset((page - 1) * page_size).limit(page_size).all()

    return {"code": 0, "message": "success", "data": {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [{
            "id": t.id,
            "task_type": t.task_type,
            "status": t.status,
            "progress": t.progress,
            "progress_message": t.progress_message,
            "error_message": t.error_message,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "finished_at": t.finished_at.isoformat() if t.finished_at else None,
        } for t in items]
    }}

# after
    total = query.count()
    items = query.order_by(AsyncTask.created_at.desc())\
        .offset((page - 1) * page_size).limit(page_size).all()

    # 批量计算每个任务的用户级序号（比该任务早创建的同用户任务数 + 1）
    item_data = []
    for t in items:
        user_seq = db.query(AsyncTask).filter(
            AsyncTask.created_by == user_id,
            AsyncTask.created_at < t.created_at
        ).count() + 1
        item_data.append({
            "id": t.id,
            "user_seq": user_seq,
            "task_type": t.task_type,
            "status": t.status,
            "progress": t.progress,
            "progress_message": t.progress_message,
            "error_message": t.error_message,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "finished_at": t.finished_at.isoformat() if t.finished_at else None,
        })

    return {"code": 0, "message": "success", "data": {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": item_data
    }}
```

### 改动2：get_task 返回加 user_seq

**文件**：`backend/app/api/task.py`

**位置**：第 35-46 行（get_task的返回部分）

```python
# before
    return {"code": 0, "message": "success", "data": {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "progress": task.progress,
        "progress_message": task.progress_message,
        "result": result_data,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }}

# after
    user_seq = db.query(AsyncTask).filter(
        AsyncTask.created_by == user_id,
        AsyncTask.created_at < task.created_at
    ).count() + 1

    return {"code": 0, "message": "success", "data": {
        "id": task.id,
        "user_seq": user_seq,
        "task_type": task.task_type,
        "status": task.status,
        "progress": task.progress,
        "progress_message": task.progress_message,
        "result": result_data,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }}
```

### 改动3：前端 TaskCenter 显示用户级序号

**文件**：`frontend/src/pages/TaskCenter.tsx`

**位置**：第 74-84 行（任务列的render）

```tsx
// before
    {
      title: '任务',
      dataIndex: 'task_type',
      width: 200,
      render: (type: string, record: any) => (
        <div>
          <div>{TASK_TYPE_NAMES[type] || type}</div>
          <div style={{ fontSize: 12, color: '#94a3b8' }}>{record.created_at?.slice(5, 16)}</div>
        </div>
      ),
    },

// after
    {
      title: '任务',
      dataIndex: 'task_type',
      width: 200,
      render: (type: string, record: any) => (
        <div>
          <div>{TASK_TYPE_NAMES[type] || type} #{record.user_seq || record.id}</div>
          <div style={{ fontSize: 12, color: '#94a3b8' }}>{record.created_at?.slice(5, 16)}</div>
        </div>
      ),
    },
```

### 验证

- 静态检查：后端import不报错，前端 `npx tsc --noEmit` 无新增错误
- 运行时验证：任务中心应显示"GEO/AEO刷新 #4"（用户级序号），而不是"#21"

---

## 修复2.5：minimax单独配置超时

### 根因

`OpenAICompatibleAdapter.__init__` 中所有平台共用 `timeout=120`，但 minimax 代理不稳定（429/503），需要更长的超时时间。

### 修复目标

给 minimax 单独配置60秒超时（其他平台保持120秒）。

### 改动1：config.py 加 MINIMAX_TIMEOUT

**文件**：`backend/app/config.py`

**位置**：第 31-34 行（MiniMax配置区）

```python
# before
    # MiniMax
    MINIMAX_API_KEY: str = ""
    MINIMAX_BASE_URL: str = ""
    MINIMAX_MODEL: str = "MiniMax-M2.7-highspeed"

# after
    # MiniMax
    MINIMAX_API_KEY: str = ""
    MINIMAX_BASE_URL: str = ""
    MINIMAX_MODEL: str = "MiniMax-M2.7-highspeed"
    MINIMAX_TIMEOUT: int = 60  # minimax代理不稳定，单独配置超时（秒）
```

### 改动2：openai_compatible.py 支持 per-platform 超时

**文件**：`backend/app/adapters/openai_compatible.py`

**位置**：第 19-26 行（`__init__`方法）

```python
# before
    def __init__(self, api_key: str, base_url: str, model: str,
                 temperature: float = 0.3, max_tokens: int = 2000):
        super().__init__(api_key, base_url, model, temperature, max_tokens)
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=120
        )

# after
    def __init__(self, api_key: str, base_url: str, model: str,
                 temperature: float = 0.3, max_tokens: int = 2000,
                 timeout: int = 120):
        super().__init__(api_key, base_url, model, temperature, max_tokens)
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )
```

### 改动3：factory.py 中 MiniMaxAdapter 传入超时

**文件**：`backend/app/adapters/factory.py`

先读取 factory.py 确认 MiniMaxAdapter 的初始化代码位置。

```
# 需要新session先 Read factory.py，找到 MiniMaxAdapter 初始化的位置，然后加 timeout 参数
# 大致改动：
# before
#     self._adapters["minimax"] = MiniMaxAdapter(
#         api_key=settings.MINIMAX_API_KEY,
#         base_url=settings.MINIMAX_BASE_URL,
#         model=settings.MINIMAX_MODEL,
#     )
#
# after
#     self._adapters["minimax"] = MiniMaxAdapter(
#         api_key=settings.MINIMAX_API_KEY,
#         base_url=settings.MINIMAX_BASE_URL,
#         model=settings.MINIMAX_MODEL,
#         timeout=settings.MINIMAX_TIMEOUT,
#     )
```

**注意**：新session必须先 Read factory.py 确认实际代码，再做精确修改。

### 验证

- 静态检查：`C:\Users\jenac\miniconda3\python.exe -c "from app.adapters import adapter_factory; print(adapter_factory.get_adapter('minimax').client.timeout)"` 应输出 60
- 运行时验证：minimax调用时超时时间为60秒

---

## 修复2.6：文章生成同步阻塞→异步任务

### 根因

`GET /api/v1/template/article/{semantic_id}` 同步调用 `ArticleGenerator.generate()`，耗时10-120秒，阻塞HTTP请求，用户等待期间不能操作，且容易超时。

### 修复目标

改为异步任务：API投递AsyncTask，立即返回task_id，前端轮询任务进度，完成后从任务结果中获取文章。

### 改动1：注册 article_generate 任务类型

**文件**：`backend/app/worker/collector_tasks.py`（或新建 article_tasks.py）

新建文件 `backend/app/worker/article_tasks.py`：

```python
"""文章生成相关任务的处理函数"""
import json
import logging
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.models.semantic import Semantic
from app.models.doctor import DoctorProfile
from app.models.content_opportunity import ContentOpportunity
from app.engines.article_generator import ArticleGenerator
from app.worker.task_registry import register_handler, ProgressCallback

logger = logging.getLogger(__name__)


def handle_article_generate(db: Session, task: AsyncTask, on_progress: ProgressCallback = None) -> dict:
    """处理文章生成任务"""
    payload = json.loads(task.payload_json or "{}")
    semantic_id = payload.get("semantic_id")
    opportunity_id = payload.get("opportunity_id")
    user_id = task.created_by

    if not semantic_id:
        raise ValueError("payload 中缺少 semantic_id")

    if on_progress:
        on_progress(1, 3, "查询语义和医生资料")

    semantic = db.query(Semantic).filter(
        Semantic.id == semantic_id, Semantic.user_id == user_id
    ).first()
    if not semantic:
        raise ValueError("语义不存在或不属于当前用户")

    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    if not profile:
        raise ValueError("请先完善医生资料")

    opportunity = None
    if opportunity_id:
        opportunity = db.query(ContentOpportunity).filter(
            ContentOpportunity.id == opportunity_id,
            ContentOpportunity.question_id == semantic_id
        ).first()

    if on_progress:
        on_progress(2, 3, "LLM生成文章中")

    generator = ArticleGenerator(db)
    result = generator.generate(semantic, profile, opportunity)

    if on_progress:
        on_progress(3, 3, "文章生成完成")

    return result


# 注册任务处理函数
register_handler("article_generate", handle_article_generate)
```

### 改动2：在 worker.py 中导入 article_tasks

**文件**：`backend/app/worker/worker.py`

**位置**：第 31-32 行（导入区）

```python
# before
import app.worker.collector_tasks  # noqa: F401
import app.worker.asset_tasks  # noqa: F401

# after
import app.worker.collector_tasks  # noqa: F401
import app.worker.asset_tasks  # noqa: F401
import app.worker.article_tasks  # noqa: F401
```

### 改动3：template.py 文章生成接口改为投递任务

**文件**：`backend/app/api/template.py`

**位置**：第 18-60 行（`generate_article_template` 函数）

```python
# before
@router.get("/article/{semantic_id}", summary="生成GEO文章（LLM优先，模板兜底）")
def generate_article_template(
    semantic_id: int,
    opportunity_id: Optional[int] = Query(None, description="内容机会ID，用于定向生成"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    semantic = db.query(Semantic).filter(
        Semantic.id == semantic_id, Semantic.user_id == user_id
    ).first()
    if not semantic:
        raise HTTPException(status_code=404, detail="语义不存在")

    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="请先完善医生资料")

    opportunity = None
    if opportunity_id:
        opportunity = db.query(ContentOpportunity).filter(
            ContentOpportunity.id == opportunity_id,
            ContentOpportunity.question_id == semantic_id
        ).first()
        if not opportunity:
            raise HTTPException(status_code=404, detail="内容机会不存在或与语义不匹配")

    generator = ArticleGenerator(db)
    result = generator.generate(semantic, profile, opportunity)

    return {
        "code": 0, "message": "success",
        "data": {
            "title": result["title"],
            "intro": result["intro"],
            "body": result["body"],
            "conclusion": result["conclusion"],
            "tags": result["tags"],
            "full_text": result["full_text"],
            "source": result.get("source", "template"),
        }
    }

# after
@router.post("/article/{semantic_id}", summary="生成GEO文章（异步任务）")
def generate_article_template(
    semantic_id: int,
    opportunity_id: Optional[int] = Query(None, description="内容机会ID，用于定向生成"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    from app.models.task import AsyncTask
    import json

    # 校验语义和资料（快速失败，不投递任务）
    semantic = db.query(Semantic).filter(
        Semantic.id == semantic_id, Semantic.user_id == user_id
    ).first()
    if not semantic:
        raise HTTPException(status_code=404, detail="语义不存在")

    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="请先完善医生资料")

    # 投递异步任务
    task = AsyncTask(
        task_type="article_generate",
        status="queued",
        created_by=user_id,
        payload_json=json.dumps({
            "semantic_id": semantic_id,
            "opportunity_id": opportunity_id,
        }, ensure_ascii=False),
        progress_message="等待执行",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "code": 0, "message": "文章生成任务已提交",
        "data": {
            "task_id": task.id,
            "status": "queued",
            "message": "文章生成中，请在任务中心查看进度",
        }
    }
```

**注意**：
- 接口从 GET 改为 POST（因为有副作用——创建任务）
- 前端需要相应改动：从直接获取文章结果改为投递任务后轮询
- 任务完成后，文章结果存在 `task.result_json` 中，前端通过 `GET /api/v1/task/{task_id}` 获取

### 改动4：前端文章生成页面改为异步轮询

**文件**：需要新session先 Read 前端调用文章生成接口的组件（可能在 ArticleEditor.tsx 或类似文件中），找到调用 `templateApi.generateArticle` 的地方，改为投递任务后轮询。

**大致逻辑**：
```tsx
// before
const res = await templateApi.generateArticle(semanticId)
setArticle(res.data)

// after
const res = await templateApi.generateArticle(semanticId)  // 现在是POST
const taskId = res.data.task_id
// 轮询任务状态
const timer = setInterval(async () => {
  const taskRes = await taskApi.get(taskId)
  if (taskRes.data.status === 'succeeded') {
    clearInterval(timer)
    setArticle(taskRes.data.result)
  } else if (taskRes.data.status === 'failed') {
    clearInterval(timer)
    message.error(taskRes.data.error_message)
  }
}, 3000)
```

**注意**：新session必须先 Read 前端相关组件，确认实际代码后再做精确修改。

### 验证

- 静态检查：后端import不报错，前端tsc无新增错误
- 运行时验证：点击生成文章，应立即返回task_id，任务中心显示"文章生成"任务执行中，完成后结果中有文章内容

---

## 修复2.7：合规检查同步阻塞→异步任务

### 根因

`POST /api/v1/compliance/check` 同步调用 `adapter.query()`，耗时5-30秒。

### 修复目标

改为异步任务，与2.6类似。

### 改动1：注册 compliance_check 任务类型

在 `backend/app/worker/article_tasks.py` 中追加（或新建 compliance_tasks.py）：

```python
def handle_compliance_check(db: Session, task: AsyncTask, on_progress: ProgressCallback = None) -> dict:
    """处理合规检查任务"""
    from app.adapters import adapter_factory
    import json as _json

    payload = _json.loads(task.payload_json or "{}")
    title = payload.get("title", "")
    content = payload.get("content", "")
    platform = payload.get("platform", "")

    if on_progress:
        on_progress(1, 2, "LLM合规检测中")

    # 构建prompt（复用compliance.py中的逻辑）
    from app.api.compliance import PLATFORM_RULES
    rules = PLATFORM_RULES.get(platform, [])
    rules_text = "\n".join([f"{i+1}. {r}" for i, r in enumerate(rules)]) if rules else "通用内容合规规则"

    prompt = f"""请作为内容合规审查员，检测以下文章是否符合{platform}平台的发布规则。

平台规则：
{rules_text}

文章标题：{title}
文章正文：{content}

请按以下JSON格式返回检测结果（只返回JSON，不要其他文字）：
{{
  "passed": true/false,
  "score": 0-100的分数,
  "issues": [
    {{
      "level": "error" / "warning" / "info",
      "rule": "违反的规则",
      "message": "问题描述",
      "suggestion": "修改建议"
    }}
  ]
}}
"""

    adapter = adapter_factory.get_adapter("glm")  # 用glm做合规检查
    if not adapter:
        return {"passed": True, "score": 100, "issues": [], "message": "无可用LLM，跳过检测"}

    result = adapter.query(prompt)
    if not result.success:
        return {"passed": True, "score": 100, "issues": [], "message": f"LLM调用失败，跳过检测: {result.error}"}

    # 解析JSON
    try:
        answer = result.answer.strip()
        if "```json" in answer:
            answer = answer.split("```json")[1].split("```")[0].strip()
        elif "```" in answer:
            answer = answer.split("```")[1].split("```")[0].strip()
        data = _json.loads(answer)
        return data
    except Exception as e:
        return {"passed": True, "score": 100, "issues": [], "message": f"解析LLM结果失败，跳过: {str(e)}"}


register_handler("compliance_check", handle_compliance_check)
```

### 改动2：worker.py 导入（如果新建了文件）

如果新建了 `compliance_tasks.py`，在 worker.py 导入区加 `import app.worker.compliance_tasks  # noqa: F401`。

### 改动3：compliance.py 接口改为投递任务

**文件**：`backend/app/api/compliance.py`

**位置**：合规检查POST接口（约第80-165行），改为投递AsyncTask。

**大致改动**：
```python
# before：同步调用adapter.query()，直接返回结果
# after：创建AsyncTask(type="compliance_check")，返回task_id
```

新session必须先 Read compliance.py 确认实际接口代码，再做精确修改。

### 改动4：前端合规检查改为异步轮询

与2.6的前端改动类似，新session先 Read 前端调用合规检查的组件，再做精确修改。

### 验证

- 静态检查：import不报错
- 运行时验证：点击合规检查，应返回task_id，任务中心显示"合规检查"任务，完成后结果中有检测结果

---

## 修复2.8：生图同步阻塞→异步任务

### 根因

`POST /api/v1/image/generate` 同步调用 `image_adapter.generate()`，耗时5-30秒。

### 修复目标

改为异步任务。

### 改动1：注册 image_generate 任务类型

在 `article_tasks.py` 中追加（或新建 image_tasks.py）：

```python
def handle_image_generate(db: Session, task: AsyncTask, on_progress: ProgressCallback = None) -> dict:
    """处理生图任务"""
    from app.adapters import adapter_factory
    import json as _json

    payload = _json.loads(task.payload_json or "{}")
    prompt = payload.get("prompt", "")
    width = payload.get("width", 1024)
    height = payload.get("height", 1024)
    n = payload.get("n", 1)
    style = payload.get("style")

    if on_progress:
        on_progress(1, 2, "生图中")

    image_adapter = adapter_factory.get_image_adapter()
    if not image_adapter:
        raise ValueError("生图适配器不可用")

    result = image_adapter.generate(prompt=prompt, width=width, height=height, n=n, style=style)

    if on_progress:
        on_progress(2, 2, "生图完成")

    return {
        "image_urls": result.image_urls,
        "task_id": result.task_id,
        "status": result.status,
        "width": result.width,
        "height": result.height,
    }


register_handler("image_generate", handle_image_generate)
```

### 改动2：image.py 接口改为投递任务

**文件**：`backend/app/api/image.py`

**位置**：第 21-59 行（`generate_image` 函数），改为投递AsyncTask。

**大致改动**：
```python
# before：同步调用image_adapter.generate()，直接返回图片URL
# after：创建AsyncTask(type="image_generate")，返回task_id
```

新session必须先 Read image.py 确认实际代码，再做精确修改。

### 改动3：前端生图改为异步轮询

新session先 Read 前端调用生图的组件，再做精确修改。

### 验证

- 静态检查：import不报错
- 运行时验证：点击生图，应返回task_id，任务中心显示"生图"任务，完成后结果中有图片URL

---

## 修复2.9：定时采集不走队列→投递AsyncTask

### 根因

`main.py` 的 `scheduled_collect()` 直接调用 `CollectorEngine.collect_one_question()`，同步执行，阻塞定时任务线程；且查的是 Question 表（项目已迁移到 Semantic 表）。

### 修复目标

定时采集改为投递 AsyncTask，由 Worker 执行；改查 Semantic 表。

### 改动

**文件**：`backend/app/main.py`

**位置**：第 61-82 行（`scheduled_collect` 函数）

```python
# before
def scheduled_collect():
    """定时采集任务：每天自动采集所有启用的问题"""
    try:
        logger.info("⏰ 定时采集任务开始执行")
        db = SessionLocal()
        collector = CollectorEngine(db)
        questions = db.query(Question).filter(Question.status == True).all()
        logger.info(f"待采集问题数: {len(questions)}")

        success_count = 0
        for q in questions:
            try:
                records = collector.collect_one_question(q, detect_round=1)
                if any(r.mentioned for r in records):
                    success_count += 1
            except Exception as e:
                logger.error(f"采集问题 [{q.id}] 失败: {e}")

        db.close()
        logger.info(f"✅ 定时采集任务完成，成功提及: {success_count}/{len(questions)}")
    except Exception as e:
        logger.error(f"❌ 定时采集任务异常: {e}")

# after
def scheduled_collect():
    """定时采集任务：每天自动为所有有启用语义的用户投递采集任务"""
    try:
        import json
        from app.models.task import AsyncTask
        from app.models.semantic import Semantic
        from app.models.doctor import DoctorProfile

        logger.info("⏰ 定时采集任务开始执行")
        db = SessionLocal()

        # 查找所有有启用语义的用户
        user_ids = [
            row[0] for row in
            db.query(Semantic.user_id).filter(
                Semantic.is_active == True,
                Semantic.user_id.isnot(None)
            ).distinct().all()
        ]
        logger.info(f"待采集用户数: {len(user_ids)}")

        task_count = 0
        for user_id in user_ids:
            try:
                # 检查用户是否有医生资料
                profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
                if not profile:
                    logger.warning(f"用户 [{user_id}] 无医生资料，跳过定时采集")
                    continue

                # 检查是否已有running/queued的采集任务，避免重复投递
                existing = db.query(AsyncTask).filter(
                    AsyncTask.created_by == user_id,
                    AsyncTask.task_type == "geo_refresh",
                    AsyncTask.status.in_(["queued", "running"])
                ).first()
                if existing:
                    logger.info(f"用户 [{user_id}] 已有进行中的采集任务 #{existing.id}，跳过")
                    continue

                # 投递采集任务
                task = AsyncTask(
                    task_type="geo_refresh",
                    status="queued",
                    created_by=user_id,
                    payload_json=json.dumps({"user_id": user_id}, ensure_ascii=False),
                    progress_message="定时采集，等待执行",
                )
                db.add(task)
                db.commit()
                task_count += 1
                logger.info(f"用户 [{user_id}] 定时采集任务已投递 #{task.id}")
            except Exception as e:
                logger.error(f"为用户 [{user_id}] 投递定时采集任务失败: {e}")
                db.rollback()

        db.close()
        logger.info(f"✅ 定时采集任务完成，共投递 {task_count} 个采集任务")
    except Exception as e:
        logger.error(f"❌ 定时采集任务异常: {e}")
```

**注意**：
- 从查 Question 表改为查 Semantic 表（项目已迁移）
- 从直接同步采集改为投递 AsyncTask，由 Worker 执行
- 加了防重复投递检查（已有running/queued任务则跳过）
- 加了医生资料检查（无资料则跳过）

### 验证

- 静态检查：`C:\Users\jenac\miniconda3\python.exe -c "from app.main import scheduled_collect; print('OK')"`
- 运行时验证：手动触发定时任务（或等每天10点），日志应显示"定时采集任务完成，共投递 N 个采集任务"，任务中心应出现对应的采集任务

---

## 全部完成后的统一验证

9项全部修改完成后，按以下步骤统一验证：

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
```bash
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\miniconda3\python.exe -m uvicorn app.main:app --port 8000
```
确认无 ERROR，43条路由正常注册，Worker启动正常。

### 4. 功能验证（用 liujinru 账号）

| 验证项 | 操作 | 预期结果 |
|--------|------|---------|
| 2.1 用户平台开关 | 停用deepseek后触发采集 | 日志显示"已停用平台: {'deepseek'}，采集时跳过"，不出现deepseek调用 |
| 2.2 采集并发 | 触发采集 | 日志显示"并发模式"，4平台请求几乎同时发出，单语义<50秒 |
| 2.3 用户轮询 | 用户A发多个任务后用户B发任务 | 用户B的任务被优先认领 |
| 2.4 用户级序号 | 进入任务中心 | 显示"GEO/AEO刷新 #N"（N是用户级序号，不是全局id） |
| 2.5 minimax超时 | 检查minimax adapter | timeout=60 |
| 2.6 文章生成异步 | 点击生成文章 | 立即返回task_id，任务中心显示文章生成任务，完成后有结果 |
| 2.7 合规检查异步 | 点击合规检查 | 立即返回task_id，任务中心显示合规检查任务 |
| 2.8 生图异步 | 点击生图 | 立即返回task_id，任务中心显示生图任务 |
| 2.9 定时采集 | 手动触发或等10点 | 日志显示投递N个采集任务，不直接同步采集 |

### 5. git 提交
```bash
cd C:\Users\jenac\Desktop\GEO
git add -A
git commit -m "feat: 阶段二A-核心架构修复与异步化改造（9项）"
```

---

## 注意事项

1. **2.6/2.7/2.8 异步化改造涉及前端改动**，新session必须先 Read 前端相关组件确认实际代码，再做精确修改。如果前端改动过于复杂，可以先只做后端异步化，前端轮询逻辑留到阶段二C。
2. **2.2 并发改造是最大的改动**，注意保持缩进一致，替换整个for循环。
3. **2.5 minimax超时**需要改3个文件（config.py、openai_compatible.py、factory.py），factory.py必须先Read确认实际代码。
4. **每完成一项做一次静态检查**，不要全部改完才检查，方便定位问题。
5. **异步化改造后，原有前端直接获取结果的逻辑会失效**，必须配合前端轮询改动，否则前端会报错。

## 最终输出

完成后输出报告：
1. 9项修复的状态（✅/⚠️/❌）
2. 每项实际改动的文件和行号
3. 验证结果
4. git commit hash
5. 遇到的问题和未完成项（如果有）

---

现在开始：第一步，用 Read 工具读取所有涉及的文件，确认当前代码状态。
