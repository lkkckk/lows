# 项目文件结构说明

```
law-query-system/
│
├── 📄 核心配置文件
│   ├── docker-compose.yml          # Docker 服务编排配置
│   ├── .gitignore                  # Git 忽略文件
│   ├── start.ps1                   # Windows 一键启动脚本
│   └── README.md                   # 项目主文档
│
├── 📚 文档目录
│   ├── DEPLOY.md                   # 部署指南（含问题排查）
│   ├── API_DOCS.md                 # API 接口文档
│   └── PROJECT_SUMMARY.md          # 项目实施总结
│
├── 🔧 后端服务 (backend/)
│   ├── Dockerfile                  # 后端 Docker 镜像配置
│   ├── requirements.txt            # Python 依赖清单
│   └── app/                        # 应用代码
│       ├── main.py                 # FastAPI 应用入口
│       ├── db.py                   # MongoDB 连接管理
│       ├── api/                    # API 路由层
│       │   ├── laws.py             # 法规相关接口
│       │   ├── templates.py        # 文书模板接口
│       │   └── __init__.py         # 路由聚合
│       ├── models/                 # 数据模型层
│       │   ├── schemas.py          # Pydantic 模型定义
│       │   └── __init__.py
│       └── services/               # 业务逻辑层
│           ├── law_service.py      # 法规服务（核心搜索算法）
│           ├── template_service.py # 模板服务（渲染导出）
│           └── __init__.py
│
├── 🎨 前端应用 (frontend/)
│   ├── Dockerfile                  # 前端 Docker 镜像（多阶段构建）
│   ├── nginx.conf                  # Nginx 配置（SPA 路由 + API 代理）
│   ├── package.json                # Node.js 依赖清单
│   ├── vite.config.js              # Vite 构建配置
│   ├── index.html                  # HTML 入口
│   └── src/                        # 源代码
│       ├── main.jsx                # React 应用入口
│       ├── App.jsx                 # 主应用组件（路由配置）
│       ├── App.css                 # 全局样式
│       ├── pages/                  # 页面组件
│       │   ├── LawsList.jsx        # 法规列表页
│       │   ├── LawDetail.jsx       # 法规详情页（★核心页面）
│       │   ├── GlobalSearch.jsx    # 全局搜索页
│       │   ├── TemplatesList.jsx   # 模板列表页
│       │   └── TemplateEditor.jsx  # 模板编辑器
│       ├── services/               # 服务层
│       │   └── api.js              # API 调用封装
│       └── styles/                 # 样式文件
│           └── LawDetail.css       # 法规详情页样式
│
├── 🕷️ 爬虫工具 (crawler/)
│   ├── requirements.txt            # Python 依赖
│   ├── base_spider.py              # 爬虫基类（适配器模式核心）
│   ├── import_data.py              # MongoDB 数据导入脚本
│   ├── create_sample_data.py       # 示例数据生成器
│   ├── spiders/                    # 爬虫适配器目录
│   │   └── example_spider.py       # 示例爬虫（含 TODO 指导）
│   └── output/                     # 数据输出目录（自动生成）
│       ├── laws.jsonl              # 法规数据（运行后生成）
│       ├── law_articles.jsonl      # 条文数据（运行后生成）
│       └── *_seen_urls.txt         # 已爬取 URL 记录（去重用）
│
└── 🗄️ 数据库配置 (mongodb/)
    └── init-indexes.js             # MongoDB 索引初始化脚本
```

---

## 📂 关键目录说明

### backend/app/
后端应用采用**三层架构**：
- **api/** - 路由层，负责接收请求和返回响应
- **models/** - 数据模型层，定义请求/响应格式
- **services/** - 业务逻辑层，核心算法实现

### frontend/src/
前端采用**组件化设计**：
- **pages/** - 页面级组件（对应路由）
- **services/** - API 调用封装（axios）
- **styles/** - 组件样式（CSS）

### crawler/
爬虫框架采用**适配器模式**：
- `base_spider.py` - 基础爬虫类（通用功能）
- `spiders/` - 具体网站适配器（继承基类）

---

## 🔑 核心文件解读

### 1. `backend/app/services/law_service.py`
**最重要的文件之一**，包含：
- ✅ 条号解析算法（中文数字转换）
- ✅ 单法规内搜索（条号优先，关键字备选）
- ✅ 全库跨法规搜索（MongoDB 聚合）
- ✅ 高亮片段生成

### 2. `frontend/src/pages/LawDetail.jsx`
**最复杂的前端页面**，实现：
- ✅ 条文搜索与定位
- ✅ 平滑滚动动画
- ✅ 高亮效果（5 秒自动褪去）
- ✅ URL 参数状态管理

### 3. `crawler/base_spider.py`
**可扩展爬虫框架**，提供：
- ✅ 重试机制（tenacity）
- ✅ 去重与增量抓取
- ✅ 条文自动拆分
- ✅ 中文数字转换

### 4. `mongodb/init-indexes.js`
**性能优化关键**，包含：
- ✅ 4 个集合的索引设计
- ✅ 文本索引配置（权重优化）
- ✅ 复合索引优化查询

---

## 🚀 快速定位功能代码

| 功能 | 文件位置 |
|------|---------|
| 条号解析算法 | `backend/app/services/law_service.py::parse_article_input()` |
| 全文搜索 | `backend/app/services/law_service.py::search_in_law()` |
| PDF 导出 | `backend/app/services/template_service.py::export_to_pdf()` |
| 条文定位 | `frontend/src/pages/LawDetail.jsx::handleSearch()` |
| 爬虫框架 | `crawler/base_spider.py::BaseLawSpider` |
| 数据导入 | `crawler/import_data.py::import_data()` |

---

## 📦 运行时生成的文件/目录

运行系统后，会自动生成以下文件：

```
law-query-system/
├── crawler/output/                 # 爬虫输出
│   ├── laws.jsonl
│   ├── law_articles.jsonl
│   ├── doc_templates.jsonl
│   └── *_seen_urls.txt
│
├── frontend/node_modules/          # Node.js 依赖
├── frontend/dist/                  # 生产构建产物
│
└── (Docker Volumes)                # Docker 数据卷
    └── mongodb_data/               # MongoDB 数据持久化
```

⚠️ 这些文件/目录已添加到 `.gitignore`，不会被提交到 Git。

---

## 🔧 修改指南

### 需要调整爬虫适配器
📁 文件：`crawler/spiders/example_spider.py`

找到标记为 `# ⚠️ TODO` 的部分：
1. `extract_law_links()` - 修改列表页选择器
2. `parse_law_page()` - 修改详情页选择器
3. `_extract_meta_info()` - 调整元信息提取逻辑

### 需要修改 API 接口
📁 目录：`backend/app/api/`

- 法规接口：`laws.py`
- 模板接口：`templates.py`

### 需要调整前端样式
📁 目录：`frontend/src/styles/`

或直接在组件文件中修改 `style` 属性。

### 需要添加新功能
1. 后端：在 `backend/app/services/` 添加新服务类
2. 前端：在 `frontend/src/pages/` 添加新页面
3. 更新路由：`frontend/src/App.jsx`

---

## 📊 代码统计

| 模块 | 文件数 | 代码行数（估算） |
|------|-------|----------------|
| 后端 | 12 | ~2000 行 |
| 前端 | 10 | ~1500 行 |
| 爬虫 | 5 | ~500 行 |
| 配置 | 5 | ~300 行 |
| **总计** | **32** | **~4300 行** |

---

**提示**：所有文件均包含详细的中文注释，便于理解和维护。
