# 法律文库系统 - 离线部署说明

## 最终目录结构

### 目标服务器目录结构：
```
D:\Nginx_law\                    # 独立 Nginx 目录
├── conf\
│   ├── nginx.conf               # 主配置文件（使用 nginx_law.conf）
│   └── mime.types               # MIME 类型配置
├── html\                        # 前端静态文件
│   ├── index.html
│   └── assets\
├── logs\                        # 日志目录
├── temp\                        # 临时目录
└── nginx.exe                    # Nginx 程序
```

---

## 部署步骤

### 1. 准备独立 Nginx

1. 下载 Nginx Windows 版本（或从现有 Nginx 复制）
2. 解压到 `D:\Nginx_law\`
3. 将 `nginx_law.conf` 重命名为 `nginx.conf` 放入 `D:\Nginx_law\conf\`
4. 将 `frontend\` 目录下的所有文件复制到 `D:\Nginx_law\html\`

### 2. 部署后端和数据库

1. 将 `deploy_package` 复制到目标服务器（如 `E:\law-query-system\`）
2. 以**管理员身份**运行 `deploy.bat`

### 3. 启动 Nginx

```cmd
cd D:\Nginx_law
nginx.exe
```

### 4. 验证

访问 `http://localhost:6011`

---

## 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端（Nginx） | 6011 | 独立 Nginx 实例 |
| 后端（Docker） | 4008 | FastAPI 服务 |
| MongoDB（Docker） | 27019 | 仅内网访问 |

---

## 隔离性说明

- Nginx：独立目录 `D:\Nginx_law`，端口 6011
- Docker 网络：`law_system_network`
- Docker 卷：`law_system_db_data`
- 容器名称：`law_system_backend`、`law_system_mongodb`

**不会影响目标服务器上现有的任何项目。**

---

## 部署包内容

```
deploy_package/
├── frontend/           # 前端静态文件 → 复制到 D:\Nginx_law\html\
├── mongodump/          # 数据库备份
├── law_images.tar      # Docker 镜像包
├── docker-compose.yml  # Docker 编排文件
├── deploy.bat          # 后端一键部署脚本
├── nginx_law.conf      # Nginx 配置 → 复制到 D:\Nginx_law\conf\nginx.conf
└── README.md           # 本说明文件
```
