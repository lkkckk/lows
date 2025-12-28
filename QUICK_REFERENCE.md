# ⚡ 快速参考卡片

## 🚀 一键启动

```powershell
cd law-query-system
.\start.ps1
```

访问：http://localhost:5173

---

## 📝 常用命令

### Docker 管理
```powershell
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 查看运行状态
docker-compose ps

# 查看日志
docker-compose logs -f [service_name]

# 重启服务
docker-compose restart [service_name]
```

### 数据管理
```powershell
# 生成示例数据
cd crawler
python create_sample_data.py

# 导入数据
python import_data.py

# 运行爬虫
cd spiders
python example_spider.py
```

### 本地开发
```powershell
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

---

## 🔗 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端应用 | http://localhost:5173 | React SPA |
| 后端 API | http://localhost:8000 | FastAPI |
| API 文档 | http://localhost:8000/docs | Swagger UI |
| MongoDB | mongodb://localhost:27017 | 数据库 |
| Mongo Express | http://localhost:8081 | 数据库管理（debug） |

---

## 📂 重要文件

| 文件 | 用途 |
|------|------|
| `README.md` | 项目主文档 |
| `DEPLOY.md` | 部署指南 |
| `API_DOCS.md` | API 文档 |
| `PROJECT_SUMMARY.md` | 实施总结 |
| `FILE_STRUCTURE.md` | 文件结构说明 |

---

## 🔑 核心功能位置

| 功能 | 文件 |
|------|------|
| 条号解析 | `backend/app/services/law_service.py` |
| 全文搜索 | `backend/app/services/law_service.py` |
| PDF 导出 | `backend/app/services/template_service.py` |
| 条文定位 | `frontend/src/pages/LawDetail.jsx` |
| 爬虫框架 | `crawler/base_spider.py` |

---

## ⚠️ 常见问题

### MongoDB 连接失败
```powershell
docker-compose restart mongodb
docker-compose logs mongodb
```

### 前端访问 API 404
检查后端是否运行：http://localhost:8000/docs

### 中文搜索无结果
确认索引已创建：
```powershell
docker exec law_system_mongodb mongosh law_system --eval "db.laws.getIndexes()"
```

### PDF 导出失败
确保后端容器安装了中文字体（Dockerfile 已包含）

---

## 📞 获取帮助

1. 查看 `DEPLOY.md` 中的问题排查章节
2. 查看 Docker 日志：`docker-compose logs [service]`
3. 查看浏览器控制台（F12）

---

**提示**：所有文档均使用中文编写，便于快速查找。
