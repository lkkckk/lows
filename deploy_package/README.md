# 法律检索系统 - 生产环境部署包

## 📦 包内容
- `backend_image.tar` - 后端 Docker 镜像
- `mongo_image.tar` - MongoDB 数据库镜像
- `mongodb_dump/` - 数据库备份（38部法规，3530条条文）
- `docker-compose.yml` - 服务编排配置
- `deploy.bat` - 一键部署脚本
- `frontend/` - 前端静态文件（请单独部署到 Nginx）

## 🚀 部署步骤

1. 将整个 `deploy_package` 文件夹拷贝到生产电脑（如 `E:\deploy_package`）
2. 双击运行 `deploy.bat`
3. 前端部署：将 `frontend/` 目录内容部署到 Nginx 或其他静态服务器

## ⚙️ 端口配置
- 后端 API: `4008` (映射到容器内 `8000`)
- MongoDB: `27019` (映射到容器内 `27017`)

## 🔧 前端配置
确保前端的 API 地址指向 `http://<服务器IP>:4008/api`
