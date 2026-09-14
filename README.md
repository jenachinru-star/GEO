# GEO 智能运营中台

**Generative Engine Optimization** - 内部AI生成式搜索引擎优化监测系统

## 项目简介

GEO智能运营中台是一套面向企业内部的AI平台曝光监测与内容运营系统。通过持续监测主流AI大模型平台（DeepSeek、GLM、豆包、通义千问等）对企业品牌、产品、行业问题的回答情况，帮助企业了解自身在AI生成内容中的曝光度、排名和情感倾向，并提供知识库管理、智能问答、竞品分析等功能。

## 技术架构

### 后端
- **框架**: Python FastAPI
- **数据库**: SQLite（预留PostgreSQL迁移接口）
- **AI适配**: OpenAI兼容接口，支持多平台切换
- **向量引擎**: 纯Python实现（256维字符n-gram哈希向量）
- **定时任务**: APScheduler（每天10:00自动采集）

### 前端
- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **UI组件**: Ant Design 5
- **图表**: ECharts
- **状态管理**: Zustand
- **HTTP客户端**: Axios

### CLI工具
- **语言**: Go
- **框架**: Cobra
- **功能**: 状态查询、问题查询、触发采集、知识库管理、竞品分析

## 目录结构

```
GEO/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── adapters/       # AI平台适配器（DeepSeek/GLM/豆包/千问）
│   │   ├── api/            # API路由（7组）
│   │   ├── engines/        # 核心引擎（采集/解析/向量/RAG）
│   │   ├── models/         # 数据模型（8张表）
│   │   ├── schemas/        # Pydantic模型
│   │   ├── services/       # 业务服务
│   │   ├── config.py       # 配置管理
│   │   ├── database.py     # 数据库连接
│   │   └── main.py         # FastAPI入口
│   ├── data/               # 数据库文件目录
│   ├── requirements.txt    # Python依赖
│   └── .env                # 环境配置（API Key等）
├── frontend/                # 前端应用
│   ├── src/
│   │   ├── api/            # API封装
│   │   ├── components/     # 通用组件
│   │   ├── pages/          # 页面组件（7个页面）
│   │   ├── router/         # 路由配置
│   │   ├── store/          # 状态管理
│   │   └── styles/         # 全局样式
│   ├── package.json
│   └── vite.config.ts
└── cli/                     # 命令行工具
    └── geo-cli/
        ├── cmd/             # 子命令
        ├── main.go
        └── go.mod
```

## 功能模块

### 1. 监测中心
- 问题管理：添加、编辑、启用/禁用监测问题
- 平台矩阵：问题×平台的排名热力图
- 采集记录：查看每次采集的原始回答和解析结果
- 手动触发：支持单个问题或全量采集
- 定时采集：每天10:00自动执行

### 2. 内容资产库
- 内容管理：录入企业宣传内容（文章、新闻、产品介绍等）
- 效果追踪：记录内容被AI引用的次数和效果评分
- 分类标签：按内容类型和标签分类管理

### 3. 统一知识库
- 知识管理：录入企业知识（公司简介、核心技术、业务范围等）
- 级别管理：public/internal/confidential三级权限
- 语义检索：基于向量的相似度检索
- 向量重建：支持手动重建所有知识条目的向量

### 4. 竞品分析
- 竞品管理：添加竞品信息和别名
- 提及监测：在采集过程中同时监测竞品提及情况
- 对比分析：多维度对比企业与竞品的曝光表现

### 5. 智能问答（RAG）
- 基于知识库：检索增强生成，回答基于企业知识库
- 多平台支持：可切换不同AI平台生成回答
- 来源标注：回答中标注引用的知识库条目
- 级别过滤：按知识级别控制可检索范围

### 6. 仪表盘
- 核心指标：监测问题数、提及率、Top1推荐率、平均排名
- 趋势图表：7天曝光趋势
- 平台对比：各平台表现对比
- 排名榜单：表现最好/最差的问题

### 7. 系统设置
- 系统信息：查看应用版本、环境、品牌配置
- 平台状态：查看各AI平台配置和启用状态
- 数据初始化：一键初始化演示数据

## 快速开始

### 环境要求
- Python 3.10+（推荐3.12）
- Node.js 18+
- Go 1.21+（仅CLI需要）

### 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（复制并修改）
cp .env.example .env
# 编辑 .env，填入API Key

# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

后端服务启动后访问：http://localhost:8000/docs 查看API文档

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端启动后访问：http://localhost:3000

### CLI编译

```bash
cd cli/geo-cli

# 安装依赖
go mod tidy

# 编译
go build -o geo-cli.exe .

# 查看帮助
./geo-cli.exe --help
```

## API平台配置

目前支持以下AI平台（OpenAI兼容接口）：

| 平台 | 配置项 | 状态 |
|------|--------|------|
| DeepSeek | DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL | ✅ 已启用 |
| GLM（智谱清言） | GLM_API_KEY / GLM_BASE_URL / GLM_MODEL | ✅ 已启用 |
| 豆包 | DOUBAO_API_KEY / DOUBAO_BASE_URL / DOUBAO_MODEL | ⏳ 预留 |
| 通义千问 | QWEN_API_KEY / QWEN_BASE_URL / QWEN_MODEL | ⏳ 预留 |

在 `backend/.env` 中配置对应平台的API Key和Base URL即可启用。

## 数据库表结构

1. **geo_platform** - AI平台配置
2. **geo_question** - 监测问题
3. **geo_monitor_record** - 监测记录（问题×平台×日期×轮次）
4. **geo_content** - 内容资产
5. **geo_knowledge** - 知识库条目
6. **geo_competitor** - 竞品信息
7. **geo_competitor_record** - 竞品监测记录
8. **geo_user** - 用户（预留）

## 开发说明

### 新增AI平台适配器
1. 在 `app/adapters/` 下创建新平台文件，继承 `BaseAdapter`
2. 实现 `query()` 和 `get_platform_code()` 方法
3. 在 `app/adapters/factory.py` 中注册新适配器
4. 在 `app/config.py` 中添加配置项
5. 在 `.env` 中添加环境变量

### 数据库迁移
当前使用SQLite，如需迁移到PostgreSQL：
1. 修改 `.env` 中的 `DATABASE_URL`
2. 安装 `psycopg2-binary` 和 `pgvector`
3. 修改 `app/engines/vector.py` 使用pgvector扩展
4. 重新初始化数据库

## 已知限制

1. **向量引擎**：当前使用纯Python实现的字符n-gram哈希向量，语义理解能力有限，建议后续迁移到专业embedding模型（如text2vec、bge等）
2. **数据库**：当前使用SQLite，并发性能有限，生产环境建议迁移到PostgreSQL
3. **内容引用归因**：内容库的引用计数和效果评分目前需要手动维护，自动归因功能待开发
4. **用户权限**：用户表已预留，但登录和权限控制功能待开发
5. **前端验证**：前端页面已搭建，部分页面的完整交互验证需要在浏览器中进行

## 后续优化建议

1. **接入专业Embedding模型**：提升语义检索和RAG问答的准确性
2. **PostgreSQL + pgvector**：提升数据库性能和向量检索效率
3. **内容自动归因**：通过语义匹配自动追踪内容被AI引用的情况
4. **多轮对话**：RAG问答支持多轮上下文
5. **数据导出**：支持监测数据和报告的导出（Excel/PDF）
6. **告警通知**：异常波动时自动发送告警（邮件/飞书/钉钉）
7. **用户权限系统**：完整的登录、角色、权限管理
8. **更多AI平台**：接入豆包、通义千问、文心一言等平台

## 许可证

内部使用

## 部署说明

### 环境要求
- Python 3.10+
- Node.js 18+
- SQLite（默认，零配置）

### 后端部署

```bash
cd backend
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env  # 如果有.example的话
# 编辑 .env，填入 GLM 和 MiniMax 的 API Key

# 启动
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 前端部署

```bash
cd frontend
npm install
npm run build
# dist 目录即为静态文件，用 Nginx 或任意静态服务器托管
```

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 环境变量清单

| 变量 | 说明 | 默认值 |
|------|------|--------|
| GLM_API_KEY | 智谱清言API Key | - |
| GLM_BASE_URL | GLM接口地址 | - |
| GLM_MODEL | GLM模型名 | glm-4-flash |
| MINIMAX_API_KEY | MiniMax API Key | - |
| MINIMAX_BASE_URL | MiniMax接口地址 | - |
| MINIMAX_MODEL | MiniMax模型名 | MiniMax-M2.7-highspeed |
| ARTICLE_TOOL_URL | 文章工具跳转地址 | https://ops.szcczh.com/paper-next/ |
| VIDEO_TOOL_URL | 视频工具跳转地址 | https://video.szcczh.com/ |
| ALLOWED_ORIGINS | CORS允许域名（逗号分隔） | http://localhost:3000 |
| JWT_SECRET | JWT签名密钥 | 生产环境必须修改 |
| IAM_CLIENT_ID | IAM客户端ID | - |
| IAM_CLIENT_SECRET | IAM客户端密钥 | - |
| IAM_REDIRECT_URI | IAM回调地址 | - |

### 上线前检查清单

- [ ] 修改 JWT_SECRET 为强随机字符串
- [ ] 修改 SECRET_KEY 为强随机字符串
- [ ] 配置正确的 ALLOWED_ORIGINS（生产域名）
- [ ] 运行 `python scripts/clean_test_data.py` 清理测试数据
- [ ] 确认 GLM 和 MiniMax API Key 有效
- [ ] 前端 build 无错误
- [ ] 后端启动无报错
- [ ] 完整走一遍用户流程：登录→填资料→生成语义→创作→看数据
