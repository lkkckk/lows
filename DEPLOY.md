# 快速部署指南

## 🚀 Windows 环境快速部署

### 前置要求

确保已安装：
- Docker Desktop for Windows
- Python 3.10+
- Node.js 18+

### 步骤 1: 启动 MongoDB

打开 PowerShell，进入项目目录：

```powershell
cd law-query-system
docker-compose up -d mongodb
```

等待 MongoDB 启动（约 10-15 秒），可通过以下命令检查状态：

```powershell
docker-compose ps
```

### 步骤 2: 准备示例数据（可选）

如果您还没有爬取到数据，可以使用测试数据：

```powershell
cd crawler
python create_sample_data.py
```

这将在 `crawler/output/` 目录生成示例 JSONL 文件。

### 步骤 3: 导入数据到 MongoDB

```powershell
cd crawler
pip install -r requirements.txt
python import_data.py
```

按提示选择是否清空旧数据（首次运行选 `y`）。

### 步骤 4: 启动后端服务

#### 方式 A: Docker（推荐）

```powershell
cd ..
docker-compose up -d backend
```

#### 方式 B: 本地开发

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

访问 http://localhost:8000/docs 验证后端是否正常运行。

### 步骤 5: 启动前端应用

#### 方式 A: Docker

```powershell
docker-compose up -d frontend
```

访问 http://localhost:5173

#### 方式 B: 本地开发

```powershell
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

---

## 🐛 常见问题排查

### 问题 1: MongoDB 连接失败

**症状**：后端启动时报错 "Connection refused"

**解决方案**：
```powershell
# 重启 MongoDB
docker-compose restart mongodb

# 查看日志
docker-compose logs mongodb
```

### 问题 2: 前端访问 API 时 404

**症状**：浏览器控制台显示 API 请求失败

**解决方案**：
1. 确认后端正在运行：访问 http://localhost:8000/docs
2. 检查 Vite 代理配置：`frontend/vite.config.js`

### 问题 3: 中文搜索无结果

**症状**：搜索中文关键字没有结果

**解决方案**：
1. 确认数据已正确导入：
```powershell
docker exec law_system_mongodb mongosh law_system --eval "db.laws.countDocuments({})"
```

2. 确认索引已创建：
```powershell
docker exec law_system_mongodb mongosh law_system --eval "db.laws.getIndexes()"
```

### 问题 4: PDF 导出失败

**症状**：点击"导出 PDF"时报错

**解决方案**：
确保后端容器已安装中文字体（Dockerfile 中已包含）。如果是本地运行，需要手动安装：

```powershell
# 仅 Linux 环境
sudo apt-get install fonts-noto-cjk
```

---

## 📊 数据验证

导入数据后，可通过以下方式验证：

### 1. MongoDB Express（可选）

启动数据库管理界面：

```powershell
docker-compose --profile debug up -d mongo-express
```

访问 http://localhost:8081
- 用户名：admin
- 密码：admin123

### 2. API 测试

访问 http://localhost:8000/docs，测试以下接口：

- `GET /api/laws/` - 获取法规列表
- `POST /api/laws/search` - 全局搜索
- `GET /api/templates/` - 获取模板列表

---

## 🔄 更新数据

### 增量更新

爬虫自动支持增量抓取（基于 seen_urls 机制）：

```powershell
cd crawler/spiders
python example_spider.py
cd ..
python import_data.py
```

选择 `n` 不清空旧数据，新数据会被追加或更新。

### 全量刷新

如需完全重新导入：

```powershell
cd crawler
python import_data.py
# 选择 y 清空旧数据
```

---

## 🛑 停止服务

停止所有容器：

```powershell
docker-compose down
```

保留数据并停止：

```powershell
docker-compose stop
```

清除所有数据（⚠️ 危险操作）：

```powershell
docker-compose down -v
```

---

## 📝 生产环境部署注意事项

1. **修改默认密码**：
   - MongoDB 添加用户认证
   - Mongo Express 更改默认密码

2. **配置 HTTPS**：
   - 使用 Nginx 反向代理
   - 配置 SSL 证书

3. **性能优化**：
   - 启用 MongoDB 副本集
   - 配置 Redis 缓存
   - 使用 PM2 管理 Node.js 进程

4. **监控告警**：
   - 集成 Prometheus + Grafana
   - 配置日志收集（ELK）

5. **备份策略**：
   ```powershell
   # MongoDB 备份
   docker exec law_system_mongodb mongodump --out /data/backup
   ```

---

## 📞 技术支持

如有问题，请检查：
1. Docker 日志：`docker-compose logs [service_name]`
2. 后端日志：查看控制台输出
3. 前端控制台：浏览器 DevTools

---

**祝使用愉快！** 🎉
