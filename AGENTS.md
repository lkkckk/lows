# AGENTS.md
# 本仓库的代理编码指南（供 agentic coding agents 使用）

## 范围与安全（强制）
- 本仓库涉及敏感警务数据；修改需最小化，避免暴露数据与内部配置。
- 不要新增/提交任何密钥或真实凭据；不要读取、传播或提交 `.env*`（即使仓库里存在）。
- 不要在日志/错误信息中输出个人信息、IP 白名单、管理员口令等敏感字段。
- 未明确要求时避免大范围重构；修 bug 只做最小修复。

## 仓库结构（落点）
- `backend/` FastAPI（API 路由、服务层、数据模型、脚本）。
- `frontend/` React 18 + Vite（页面、服务、样式）。
- `crawler/` Python 爬虫 + 数据导入/修复脚本。
- `mongodb/` MongoDB 初始化脚本（索引）。
- 文档：`README.md`、`DEPLOY.md`、`QUICK_REFERENCE.md`、`API_DOCS.md`、`FILE_STRUCTURE.md`。

## 构建/运行命令

### Docker Compose（推荐：完整栈）
- 启动全部：`docker-compose up -d`
- 仅启动 MongoDB：`docker-compose up -d mongodb`
- 启动后端：`docker-compose up -d backend`
- 启动前端：`docker-compose up -d frontend`
- 查看状态：`docker-compose ps`
- 查看日志：`docker-compose logs -f <service>`
- 停止（不删）：`docker-compose stop`
- 停止并删除：`docker-compose down`
- 数据清理（危险）：`docker-compose down -v`

`docker-compose.yml` 端口（以该文件为准）：
- MongoDB：`27019:27017`
- Backend：`4008:8000`（容器内 uvicorn 监听 8000）
- Frontend：`6011:6011`
- Embedding：`8002:8000`

可选调试服务（Mongo Express）：
- compose 里使用 `profiles: [debug]`；启动：`docker-compose --profile debug up -d mongo-express`
- 默认账号在 compose 里是弱口令；生产环境务必修改。

### Windows 一键启动
- PowerShell：`./start.ps1`
  - 自动启动 MongoDB；若缺数据则生成示例数据并导入；再启动 backend/frontend。
  - 注意：脚本里展示的 URL/端口可能与 `docker-compose.yml` 不一致，优先相信 compose 配置。

### 后端本地开发（FastAPI）
- 安装依赖：`pip install -r backend/requirements.txt`
- 启动（本地）：`uvicorn app.main:app --host 0.0.0.0 --port 4008 --reload`
- API 前缀：后端在 `backend/app/main.py` 中注册 `/api`。

### 前端本地开发（React + Vite）
- 安装依赖：在 `frontend/` 目录执行 `npm install`
- 启动开发：`npm run dev`
- 构建：`npm run build`
- 预览：`npm run preview`

### 爬虫与数据导入（离线/内网常用）
- 安装依赖：`pip install -r crawler/requirements.txt`
- 生成示例数据：`python crawler/create_sample_data.py`
- 导入数据：`python crawler/import_data.py`
- 批量抓取 + 导入：`python crawler/run_batch.py`

### 搜索引擎（可选：OpenSearch/Elasticsearch）
- 重建索引并从 MongoDB 重新导入：`python backend/scripts/search_engine_reindex.py --recreate`

### 向量（可选：Embedding + Vector Search）
- 启动 embedding：`docker-compose up -d embedding`
- 批量向量化：`python backend/scripts/init_vectors.py`

## 测试/单测（尤其是“跑单个测试”）
- 本仓库目前没有 pytest/vitest/jest 等统一测试框架；“测试”主要是脚本型自检。
- 跑一个后端自检脚本（单个测试）：
  - `python backend/scripts/test_api.py`（需要后端已启动在 `http://localhost:4008`）
  - `python backend/scripts/test_search_logic.py`（本地纯逻辑）
  - `python backend/scripts/test_ai_search.py`（需要 MongoDB）
  - `python backend/scripts/test_vector_search.py`（需要 embedding 服务 + MongoDB）

### 其他常用自检/维护脚本（按需）
- `python backend/scripts/check_law_db.py`（检查 MongoDB 中数据是否符合预期）
- `python backend/scripts/audit_laws.py`（统计/审计数据库覆盖范围）
- `python backend/scripts/init_vectors.py`（批量生成 embedding；依赖 embedding 服务）
- `python backend/scripts/embedding_server.py`（本地启动一个简易 embedding HTTP 服务）
- `python backend/scripts/download_model.py`（下载离线模型；需要手动安装依赖）
- `python crawler/check_all.py`、`python crawler/check_db.py` 等（crawler 目录下多为一次性检查脚本）

## Lint/格式化
- 当前未配置 repo 级别的 Python/JS linter/formatter（未发现 ESLint/Prettier/Ruff/Black 等配置）。
- 代码风格以“就地遵循”为准：保持你编辑的文件原有缩进、引号、换行习惯。

## 环境变量（仅列 key，不包含任何值）
- 通用：`MONGODB_URL`、`MONGODB_DB`
- 后端：`CORS_ORIGINS`、`LOG_LEVEL`、`ADMIN_PASSWORD`、`HOST`、`PORT`
- 前端（Vite）：`VITE_PORT`、`VITE_BACKEND_HOST`、`VITE_BACKEND_PORT`、`VITE_API_URL`
- 搜索引擎：`SEARCH_ENGINE_URL` / `OPENSEARCH_URL` / `ELASTICSEARCH_URL`、`SEARCH_ENGINE_INDEX`、`SEARCH_ENGINE_ANALYZER`、`SEARCH_ENGINE_USER`、`SEARCH_ENGINE_PASSWORD`、`SEARCH_ENGINE_VERIFY_SSL`、`SEARCH_ENGINE_TIMEOUT`、`SEARCH_ENGINE_BATCH_SIZE`
- 向量/Embedding：`EMBEDDING_SERVICE_URL`、`VECTOR_SEARCH_ENABLED`、`MODEL_PATH`

## 代码风格与约定（以仓库现有实现为准）

### 通用
- UTF-8（`.editorconfig` 仅约束 `charset = utf-8`；无全局格式化器）。
- 变更要小：避免“顺手重排/重命名/大幅格式化”。

### Python（backend/ 与 crawler/）
- 命名：模块/函数/变量 `snake_case`；类 `PascalCase`。
- 类型：尽量补齐类型注解；Pydantic 模型集中在 `backend/app/models/schemas.py`。
- 异步：FastAPI 路由与服务层使用 `async/await`；DB 用 Motor（`AsyncIOMotorDatabase`）。
- import：保持标准库/三方/本地分组；本地包路径使用 `app.*`（如 `from app.services import LawService`）。
- 脚本：`backend/scripts/` 与 `crawler/` 下大量是一次性脚本，允许 `print()` 输出，但不要打印敏感数据。

### 数据库与集合
- MongoDB 连接封装：`backend/app/db.py`（FastAPI 启动时连接，lifespan 里关闭）。
- 主要集合：`laws`、`law_articles`、`doc_templates`、`doc_instances`（见 `backend/app/db.py` 常量）。

### FastAPI 分层与错误处理
- 路由薄、服务厚：路由在 `backend/app/api/`，业务在 `backend/app/services/`。
- 新增路由：在 `backend/app/api/` 新建 router，并在 `backend/app/api/__init__.py` 注册。
- 统一响应：优先返回 `APIResponse(success=True, data=..., pagination=...)`。
- 错误处理（遵循现有模式）：
  - 依赖注入里如果 `async_db is None`：`raise HTTPException(status_code=503, detail='数据库未连接')`
  - 路由里 `try/except` 包住 service 调用；404/400 用语义化 `HTTPException`；其他异常映射 500。

### API 约定（与文档一致）
- API 基础前缀：`/api`（见 `backend/app/main.py`）。
- 分页参数：`page`（从 1 开始）、`page_size`。
- 统一响应模型：`APIResponse`（success/data/pagination/error），见 `backend/app/models/schemas.py`。

### JavaScript/React（frontend/）
- 组件：函数组件 + hooks；路由：React Router v6（`Routes/Route/Navigate`）。
- API：统一走 `frontend/src/services/api.js`（axios 实例 + 拦截器）；不要在页面里散落 `fetch/axios`。
- 鉴权：管理接口用 `X-Admin-Token`（来源 `localStorage.adminToken`），见 `frontend/src/services/api.js`。
- 风格（从现有文件抽象）：单引号、分号结尾、4 空格缩进、camelCase 命名。
- 样式：以 `className + .css` 为主（如 `frontend/src/styles/LawDetail.css`），必要时可用内联 style 对象。

### 前端代理与端口
- `frontend/vite.config.js`：Vite dev server 端口来自 `VITE_PORT`（默认 6011），并将 `/api` 代理到 `VITE_BACKEND_HOST:VITE_BACKEND_PORT`。
- `frontend/src/services/api.js`：axios 默认 `baseURL: '/api'`，依赖 Vite proxy 或 Nginx 反代。

## 关键文件速查（改动落点）
- 后端路由聚合：`backend/app/api/__init__.py`
- 后端入口与 /api 注册：`backend/app/main.py`
- 检索/条号解析核心：`backend/app/services/law_service.py`
- 模板渲染/导出：`backend/app/services/template_service.py`
- 可选搜索引擎客户端：`backend/app/services/search_engine.py`
- embedding 客户端：`backend/app/services/embedding_client.py`
- 前端路由入口：`frontend/src/App.jsx`
- 前端 API 封装：`frontend/src/services/api.js`

## 常见坑/注意点
- 端口信息在文档里有历史差异：优先相信 `docker-compose.yml` 和实际运行日志。
- PDF/DOCX 导出是“可选依赖”路径：`backend/app/services/template_service.py` 会在依赖缺失时禁用功能。
- IP 白名单控制见 `backend/app/api/ip_filter.py`；不要在 PR/日志里暴露具体白名单内容。
- 管理鉴权是“极简实现”（token=管理员口令，前端存 localStorage）；涉及安全改造需先沟通再动。

## Cursor/Copilot 规则
- 未发现 Cursor 规则（未找到 `.cursor/` 或 `.cursorrules`）。
- 未发现 Copilot 指令（未找到 `.github/copilot-instructions.md`）。
