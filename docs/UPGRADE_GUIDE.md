# 生产环境升级指南：向量语义搜索 + Function Calling

> ⚠️ **适用场景**：生产机已运行旧版本项目，需要升级到支持向量语义搜索的新版本

## 🚀 极速升级方案（推荐）

我们准备了自动化脚本，只需两步即可完成：

### 第一步：在【开发机】构建升级包

1. 双击运行 `deploy_package\build_upgrade_package.bat`
2. 等待脚本执行完毕（会自动构建后端镜像、复制 Embedding 镜像等）
3. 将生成的 `deploy_package\upgrade_package` 文件夹里的**所有内容**，复制到 U 盘。

### 第二步：在【生产机】执行升级

1. 将 U 盘里的文件，覆盖到生产机的部署目录（例如 `C:\law-query-system`）
   - > 注意：是复制 upgrade_package 目录下的**内容**，不是复制整个目录
2. 双击运行 `upgrade_production.bat`
3. 等待脚本自动备份、停止服务、加载镜像、启动服务并初始化向量。
4. 看到 "Upgrade Completed Successfully!" 即表示成功。

---

## 🔧 手动升级步骤（备用）

如果脚本执行失败，请参考以下手动步骤：

### 📦 需要准备的文件（在开发机上准备）

将以下文件复制到 U 盘或通过内网传输到生产机：

```
升级包/
├── embedding.tar          # 向量模型 Docker 镜像 (~10GB)
├── backend_image.tar      # 新版后端镜像 (包含新代码)
├── docker-compose.yml     # 更新后的编排文件
├── init_embedding.bat     # 向量初始化脚本
└── load_embedding_image.bat
```

### 如何生成这些文件

**在开发机上执行**：

```powershell
# 1. 构建最新后端镜像
cd d:\law-query-system
docker build -t law_system_backend:latest -f backend/Dockerfile backend/

# 2. 导出后端镜像
docker save -o deploy_package/backend_image.tar law_system_backend:latest

# 3. 如果还没有 embedding.tar，构建它
.\prepare_offline_embedding.bat

# 4. 复制 embedding.tar 到 deploy_package
copy backend\embedding.tar deploy_package\
```

---

## 🔄 生产机升级步骤

### 第一步：备份现有环境

```powershell
# 进入部署目录
cd C:\law-query-system  # 或您的实际部署路径

# 备份当前配置
copy docker-compose.yml docker-compose.yml.backup
```

### 第二步：停止现有服务

```powershell
docker-compose stop backend
```

### 第三步：加载新镜像

```powershell
# 从 U 盘加载新镜像
docker load -i E:\升级包\backend_image.tar
docker load -i E:\升级包\embedding.tar
```

### 第四步：更新 docker-compose.yml

将新的 `docker-compose.yml` 复制到部署目录，或手动添加以下内容：

```yaml
services:
  # ... 原有的 mongodb, backend 等服务 ...
  
  # 新增：向量 Embedding 服务
  embedding:
    image: law_system_embedding:latest
    container_name: law_system_embedding
    restart: unless-stopped
    ports:
      - "8000:8000"
    networks:
      - law_system_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 更新 backend 的环境变量
  backend:
    # ... 原有配置 ...
    environment:
      # ... 原有环境变量 ...
      - EMBEDDING_SERVICE_URL=http://embedding:8000
      - VECTOR_SEARCH_ENABLED=true
    depends_on:
      - mongodb
      - embedding  # 新增依赖
```

### 第五步：启动新服务

```powershell
# 启动所有服务（包括新的 embedding）
docker-compose up -d

# 检查服务状态
docker-compose ps
```

### 第六步：初始化向量数据

```powershell
# 运行向量初始化脚本（需要 10-30 分钟，取决于法条数量）
.\init_embedding.bat
```

或手动执行：

```powershell
docker exec law_system_backend python scripts/init_vectors.py
```

### 第七步：验证升级

```powershell
# 1. 检查 embedding 服务健康状态
curl http://localhost:8000/health

# 2. 检查向量数量
docker exec law_system_backend python -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
async def check():
    c = AsyncIOMotorClient('mongodb://mongodb:27017')
    count = await c.law_system.law_articles.count_documents({'embedding': {'$exists': True}})
    print(f'已向量化条文数量: {count}')
asyncio.run(check())
"
```

---

## ⏪ 回滚方案

如果升级出现问题，可以快速回滚：

```powershell
# 1. 停止所有服务
docker-compose down

# 2. 恢复旧配置
copy docker-compose.yml.backup docker-compose.yml

# 3. 禁用向量搜索（可选，通过环境变量）
# 在 docker-compose.yml 中设置 VECTOR_SEARCH_ENABLED=false

# 4. 重新启动
docker-compose up -d
```

---

## 📋 升级检查清单

- [ ] 已备份现有 docker-compose.yml
- [ ] 已加载 backend_image.tar
- [ ] 已加载 embedding.tar
- [ ] 已更新 docker-compose.yml（添加 embedding 服务）
- [ ] 所有容器运行正常 (`docker-compose ps`)
- [ ] embedding 服务健康检查通过
- [ ] 向量初始化完成
- [ ] AI 问法功能测试正常
