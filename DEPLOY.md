# 部署指南

## � 目录

- [生产环境部署](#-生产环境部署)
- [后端热重载（快速更新）](#-后端热重载快速更新)
- [本地开发环境](#-本地开发环境)
- [常见问题排查](#-常见问题排查)
- [数据管理](#-数据管理)

---

## 🚀 生产环境部署

### 前置要求

服务器需要安装：
- Docker
- Docker Compose

### 部署步骤

#### 1. 上传部署包到服务器

将 `deploy_package` 目录上传到服务器：

```bash
# 目录结构
deploy_package/
├── docker-compose.yml    # Docker 编排配置
├── backend/              # 后端代码（首次需要复制）
└── frontend/
    ├── dist/             # 前端构建产物
    └── nginx.conf        # Nginx 配置
```

#### 2. 首次部署

```bash
# 进入部署目录
cd /path/to/deploy_package

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看后端日志
docker-compose logs -f backend
```

#### 3. 访问验证

- 前端：`http://服务器IP:6011`
- 后端 API：`http://服务器IP:4008/docs`

---

## 🔄 后端热重载（快速更新）

生产环境已配置热重载，修改后端代码后**无需重新构建镜像**。

### 更新步骤

#### 在开发机上（Windows）

```powershell
# 将修改后的后端代码上传到服务器
scp -r .\backend user@server:/path/to/deploy_package/
```

#### 代码自动生效

上传完成后，uvicorn 会自动检测文件变化并重启（约 1-3 秒）。

如需手动重启：

```bash
# 在服务器上
docker-compose restart backend
```

### 查看热重载日志

```bash
docker-compose logs -f backend
```

看到类似以下输出表示热重载成功：
```
WARNING:  WatchFiles detected changes in 'app/xxx.py'. Reloading...
INFO:     Started server process
```

---

## 💻 本地开发环境

### 前置要求

- Docker Desktop for Windows
- Python 3.10+
- Node.js 18+

### 启动步骤

#### 1. 启动 MongoDB

```powershell
cd law-query-system
docker-compose up -d mongodb
```

#### 2. 启动后端

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

访问 http://localhost:8000/docs 验证。

#### 3. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

访问 http://localhost:6011

---

## 🐛 常见问题排查

### MongoDB 连接失败

**症状**：后端启动时报错 "Connection refused"

**解决**：
```bash
docker-compose restart mongodb
docker-compose logs mongodb
```

### 前端 API 请求 404

**症状**：浏览器控制台显示 API 请求失败

**解决**：
1. 确认后端正在运行：`docker-compose ps`
2. 检查端口配置是否正确

### 中文搜索无结果

**解决**：
```bash
# 确认数据已导入
docker exec law_system_mongodb mongosh law_system --eval "db.laws.countDocuments({})"
```

---

## 📊 数据管理

### 导入数据

```powershell
cd crawler
pip install -r requirements.txt
python import_data.py
```

### 增量更新

```powershell
cd crawler/spiders
python example_spider.py
cd ..
python import_data.py  # 选择 n 不清空旧数据
```

### 数据备份

```bash
docker exec law_system_mongodb mongodump --out /data/backup
```

---

## 🛑 服务管理

### 停止服务

```bash
docker-compose stop
```

### 重启服务

```bash
docker-compose restart
```

### 停止并清理

```bash
docker-compose down      # 停止并删除容器
docker-compose down -v   # ⚠️ 同时删除数据卷
```

---

## 📝 生产环境注意事项

1. **安全配置**：修改 MongoDB 和 Mongo Express 默认密码
2. **HTTPS**：配置 Nginx 反向代理和 SSL 证书
3. **备份**：定期备份 MongoDB 数据
4. **监控**：配置日志收集和告警

---

**祝使用愉快！** 🎉
