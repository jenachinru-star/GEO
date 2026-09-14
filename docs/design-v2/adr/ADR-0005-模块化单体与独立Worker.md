# ADR-0005：模块化单体与独立 Worker

状态：Accepted  
日期：2026-09-14

## 问题

同步采集阻塞 API；API 内嵌 Scheduler/Worker 在多进程部署会重复执行。但当前规模不足以支撑微服务成本。

## 选择

保留一个 FastAPI 模块化单体和 PostgreSQL，另运行一个独立采集 Worker；任务初期由数据库队列驱动。

## 理由

能建立任务恢复、幂等、成本和部署边界，又避免 Redis/Celery/Kafka/Kubernetes 的超前复杂度。

## 过渡

当前内嵌 Worker 只允许本地开发。生产默认必须关闭 AUTO_START_WORKER，并确保 Scheduler 只有一个实例。

## 重新评估条件

日任务数、并发、优先级和重试需求超过数据库队列能力，或 Worker 需要独立扩缩容时，再评估 Redis/Celery；模块出现独立安全/发布周期时再评估微服务。
