# P0紧急修复指令：2个Bug修复

> 本指令修复2个P0级Bug：①测试平台连接报错；②导出报告500。

## 项目信息

- 项目路径：C:\Users\jenac\Desktop\GEO
- 后端路径：C:\Users\jenac\Desktop\GEO\backend
- 前端路径：C:\Users\jenac\Desktop\GEO\frontend
- 技术栈：后端 Python FastAPI + SQLAlchemy + SQLite，前端 React 18 + TypeScript + Ant Design
- 操作系统：Windows
- git 基线：8f88b95（工作区必须干净）
- 执行模式：按需确认
- Python 路径：C:\Users\jenac\miniconda3\python.exe（必须用这个）

## 修复总览（2项）

| 编号 | Bug | 根因 | 涉及文件 |
|------|-----|------|---------|
| P0-1 | 测试平台连接报错 | 创建OpenAICompatibleAdapter时传了不接受的platform_code参数 | api/platforms.py |
| P0-2 | 导出报告500 | config.py缺少DEFAULT_BRAND_NAME字段 | config.py |

## 执行顺序

严格按 P0-1 → P0-2 的顺序执行。每完成一项做一次静态检查。

---

## P0-1：测试平台连接报错修复

### 现象

管理员在"系统设置-平台配置"页面点击"测试连接"按钮，后端报错：
```
OpenAICompatibleAdapter.__init__() got an unexpected keyword argument 'platform_code'
```

### 根因

`backend/app/api/platforms.py` 第318-319行，测试平台连接时创建 `OpenAICompatibleAdapter`，传了 `platform_code=platform_code` 参数。但 `OpenAICompatibleAdapter.__init__` 不接受 `platform_code` 参数（platform_code是类属性，应在创建后单独设置）。

对比正确写法：`backend/app/adapters/factory.py` 第151-159行，创建adapter时不传platform_code，创建后第159行 `adapter.platform_code = p.code` 单独设置。

### 修复步骤

**第一步：Read 确认代码**

用 Read 工具读取 `C:\Users\jenac\Desktop\GEO\backend\app\api\platforms.py`，定位第284-355行的测试平台连接接口（`test_platform_connection` 函数）。

确认第317-330行附近的代码，找到创建 `OpenAICompatibleAdapter` 的位置。

**第二步：修改代码**

找到类似以下代码（行号可能有偏差，以实际Read结果为准）：

```python
# before
adapter = OpenAICompatibleAdapter(
    platform_code=platform_code,
    api_key=api_key,
    base_url=base_url,
    model=model,
    temperature=temperature or 0.3,
    max_tokens=max_tokens or 2000,
    timeout=timeout or 30,
)
```

修改为：

```python
# after
adapter = OpenAICompatibleAdapter(
    api_key=api_key,
    base_url=base_url,
    model=model,
    temperature=temperature or 0.3,
    max_tokens=max_tokens or 2000,
    timeout=timeout or 30,
)
adapter.platform_code = platform_code
```

**关键改动**：
1. 从 `OpenAICompatibleAdapter(...)` 的参数中移除 `platform_code=platform_code,`
2. 在创建adapter之后，加一行 `adapter.platform_code = platform_code`

**注意**：如果实际代码中变量名不是 `platform_code`（比如是 `code` 或其他），以实际代码为准，确保移除的是传给 `__init__` 的 platform_code 参数，然后在创建后设置 `adapter.platform_code = 实际变量名`。

**第三步：静态检查**

```bash
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\miniconda3\python.exe -c "from app.api.platforms import router; print('import OK')"
```

预期输出：`import OK`

如果报错，根据错误信息修正。

---

## P0-2：导出报告500修复

### 现象

在"数据概览"页面点击"导出报告"按钮，后端返回500错误：
```
AttributeError: 'Settings' object has no attribute 'DEFAULT_BRAND_NAME'
```

### 根因

`backend/app/services/export_service.py` 第259行引用了 `settings.DEFAULT_BRAND_NAME`：
```python
ws_summary.cell(row=3, column=1, value=f"品牌: {settings.DEFAULT_BRAND_NAME}")
```

但 `backend/app/config.py` 的 `Settings` 类中没有定义 `DEFAULT_BRAND_NAME` 字段。

### 修复步骤

**第一步：Read 确认代码**

用 Read 工具读取 `C:\Users\jenac\Desktop\GEO\backend\app\config.py`，确认 `Settings` 类的字段列表。

同时 Read `C:\Users\jenac\Desktop\GEO\backend\app\services\export_service.py` 第255-265行，确认引用 `DEFAULT_BRAND_NAME` 的位置。

**第二步：修改 config.py**

在 `Settings` 类中加 `DEFAULT_BRAND_NAME` 字段。

找到 `Settings` 类的字段定义区域（通常在类的开头或中间），在合适的位置加：

```python
# 品牌配置
DEFAULT_BRAND_NAME: str = "GEO创作者中心"
```

**注意**：
- 字段类型是 `str`，默认值是 `"GEO创作者中心"`
- 加在 `Settings` 类内部，和其他字段平级
- 如果 `Settings` 类已经有类似的品牌/名称配置字段，可以加在那附近
- 如果 `config.py` 中有 `model_config = SettingsConfigDict(...)`，不需要修改，新加的字段会自动从环境变量读取（环境变量名 `DEFAULT_BRAND_NAME`）

**第三步：静态检查**

```bash
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\miniconda3\python.exe -c "from app.config import settings; print('DEFAULT_BRAND_NAME:', settings.DEFAULT_BRAND_NAME)"
```

预期输出：`DEFAULT_BRAND_NAME: GEO创作者中心`

如果报错，根据错误信息修正。

---

## 全部完成后的统一验证

2项全部修改完成后，按以下步骤统一验证：

### 1. 后端完整import检查
```bash
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\miniconda3\python.exe -c "from app.main import app; print('import OK')"
```

预期输出：`import OK`

### 2. 启动后端验证
启动后端服务，确认无ERROR启动。

### 3. 功能验证清单

| 验证项 | 操作 | 预期 |
|--------|------|------|
| P0-1 测试平台连接 | 管理员→系统设置→平台配置→点击某个平台的"测试连接" | 返回连接成功/失败信息，不再报platform_code错误 |
| P0-2 导出报告 | 数据概览→点击"导出报告" | 下载Excel文件，不再500 |

### 4. git 提交
```bash
cd C:\Users\jenac\Desktop\GEO
git add -A
git commit -m "fix: P0紧急修复-测试平台连接platform_code参数+导出报告DEFAULT_BRAND_NAME字段"
```

---

## 注意事项

1. **P0-1的行号可能有偏差**：必须先Read platforms.py确认实际代码位置，不要凭记忆修改。关键是找到创建 `OpenAICompatibleAdapter(` 的地方，移除其中的 `platform_code=` 参数，然后在后面加 `adapter.platform_code = ...`。

2. **P0-2的字段加在Settings类内部**：不要加在类外面，不要加在其他类里。必须是 `Settings` 类的字段。

3. **这两个都是小改动**：每个改动只有几行代码，不要过度修改其他内容。

4. **修改后必须做静态检查**：确保import不报错。

5. **如果启动后端后发现其他问题**：记录下来，不要在本次修复中处理，本次只修这2个P0 Bug。

## 最终输出

完成后输出报告：
1. 2项修复的状态（✅/⚠️/❌）
2. 每项实际改动的文件和行号
3. 验证结果
4. git commit hash
5. 遇到的问题（如果有）

---

现在开始：第一步，用 Read 工具读取 platforms.py 和 config.py，确认当前代码状态。
