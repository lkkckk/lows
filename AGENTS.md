# AGENTS.md
# 本仓库的代理编码指南

## 范围与安全
- 本仓库涉及敏感警务数据；修改需最小化，避免暴露数据。
- 不要提交密钥或真实凭据；不要读取或提交 `.env` 文件。
- 优先遵循既有模式，未明确要求时避免大范围重构。

## 仓库结构
- `backend/` FastAPI 服务（API 路由、服务层、数据模型）。
- `frontend/` React 18 + Vite 应用（页面、服务、样式）。
- `crawler/` Python 爬虫与数据导入工具。
- `mongodb/` MongoDB 初始化脚本（索引）。
- 文档：`README.md`、`DEPLOY.md`、`QUICK_REFERENCE.md`、`API_DOCS.md`、`FILE_STRUCTURE.md`。

## 构建、运行与测试命令

### Docker Compose（推荐用于完整栈）
- 仅启动 MongoDB：`docker-compose up -d mongodb`
- 启动后端：`docker-compose up -d backend`
- 启动前端：`docker-compose up -d frontend`
- 启动全部：`docker-compose up -d`
- 查看日志：`docker-compose logs -f <service>`
- 停止：`docker-compose stop`
- 停止并删除：`docker-compose down`

### PowerShell 快速启动
- Windows 一键启动：`./start.ps1`
  - 自动启动 MongoDB、示例数据（如缺失）、后端与前端。

### 后端本地开发（FastAPI）
- 安装依赖：`pip install -r backend/requirements.txt`
- 启动开发服务：`uvicorn app.main:app --host 0.0.0.0 --port 4008 --reload`
  - 注意：文档某些位置写 8000；Docker 将 4008 映射到 8000。

### 前端本地开发（React + Vite）
- 安装依赖：`npm install`（在 `frontend/` 目录）
- 启动开发服务：`npm run dev`
  - 端口可能变化（文档示例为 5173；Docker 为 6011）。如需可设置 `VITE_PORT`。

### 爬虫与数据导入
- 安装依赖：`pip install -r crawler/requirements.txt`
- 运行爬虫：`python run_crawler.py`（在 `crawler/` 目录）
- 导入数据：`python import_data.py`（在 `crawler/` 目录）
- 生成示例数据：`python create_sample_data.py`（在 `crawler/` 目录）

### 搜索引擎（可选）
- 重新索引 OpenSearch/Elasticsearch：
  `python backend/scripts/search_engine_reindex.py --recreate`
  - 需要配置 `SEARCH_ENGINE_URL` 或 `OPENSEARCH_URL` 或 `ELASTICSEARCH_URL`。

### 向量服务（可选）
- 启动向量容器：`docker-compose up -d embedding`
- 生成向量：`python backend/scripts/init_vectors.py`
  - 需要 `EMBEDDING_SERVICE_URL` 且 MongoDB 运行中。

### 测试与单测使用
- 当前未配置正式测试/ lint 流水线。
- 使用 `backend/scripts/` 下的脚本作为测试：
  - `python backend/scripts/test_api.py`
  - `python backend/scripts/test_search_logic.py`
  - `python backend/scripts/test_ai_search.py`
  - `python backend/scripts/test_vector_search.py`
- 将每个脚本视为“单测”，按需运行对应脚本即可。

## 环境变量
- 后端：
  - `MONGODB_URL`（默认 `mongodb://localhost:27017` 或 Docker 的 `mongodb://mongodb:27017`）
  - `MONGODB_DB`（默认 `law_system`）
  - `CORS_ORIGINS`（逗号分隔）
  - `LOG_LEVEL`
- 前端：
  - `VITE_API_URL`（客户端默认 `/api`；本地可设为 `http://localhost:4008/api`）
  - `VITE_PORT`（可选）
- 搜索引擎：
  - `SEARCH_ENGINE_URL` / `OPENSEARCH_URL` / `ELASTICSEARCH_URL`
  - `SEARCH_ENGINE_INDEX`（默认 `law_articles`）
  - `SEARCH_ENGINE_ANALYZER`（默认 `ik_smart`）
  - `SEARCH_ENGINE_USER` / `SEARCH_ENGINE_PASSWORD`
  - `SEARCH_ENGINE_VERIFY_SSL`（默认 true）
- 向量：
  - `EMBEDDING_SERVICE_URL`（默认 `http://localhost:8002`）
  - `VECTOR_SEARCH_ENABLED`（启用向量检索）

## 代码风格与约定

### 通用
- 编码为 UTF-8（`.editorconfig` 设置 `charset = utf-8`）。
- 修改范围尽量小；遵循所修改模块的既有模式。

### Python（后端与爬虫）
- 使用类型注解与 Pydantic 模型（`BaseModel`、`Field`）。
- API 路由保持薄；业务逻辑放在 `backend/app/services/`。
- 使用 Motor 的 async/await 进行 DB 操作。
- API 路由的错误处理模式：
  - 用 `try/except` 包裹服务调用并抛出 `HTTPException`。
  - 保持 404 与 500 等语义区分。
- 命名：变量/函数/模块采用 `snake_case`。

### FastAPI API 约定
- API 路由位于 `backend/app/api/`，并统一注册在 `/api` 前缀下。
- 响应使用统一结构（`APIResponse`：`success`、`data`、`pagination`、`error`）。
- 分页参数使用 `page` 与 `page_size`。

### JavaScript/React（前端）
- 使用函数组件与 hooks（`useState`、`useEffect` 等）。
- 使用 React Router v6（`Routes`、`Route`、`Navigate`）。
- API 调用统一走 `frontend/src/services/api.js`。
- 样式以 className + CSS 文件为主，必要时使用内联样式。
- 参考 `frontend/src` 的既有风格：
  - 字符串使用单引号。
  - 语句以分号结尾。
  - 4 空格缩进。
  - 变量与函数使用 camelCase。

### 错误处理
- 前端 API 客户端使用 Axios 拦截器；新增 API 调用放在同一客户端内。
- 后端错误需显式抛出 `HTTPException`，避免吞掉异常。

## 功能落点
- 新增 API 路由：`backend/app/api/`，并在 `backend/app/api/__init__.py` 中注册。
- 新增服务：`backend/app/services/`。
- 数据模型与请求/响应 schema：`backend/app/models/schemas.py`。
- 新增页面：`frontend/src/pages/`，并在 `frontend/src/App.jsx` 中注册路由。
- 共享 API 调用：`frontend/src/services/api.js`。

## 数据与检索行为
- 条文解析与检索逻辑集中在 `backend/app/services/law_service.py`。
- 修改搜索逻辑时需保持单法规与全库搜索一致。
- 可选搜索引擎由环境变量控制；保留降级路径。

## Cursor/Copilot 规则
- 未发现 Cursor 规则（`.cursor/rules/` 或 `.cursorrules`）。
- 未发现 Copilot 指令（`.github/copilot-instructions.md`）。
