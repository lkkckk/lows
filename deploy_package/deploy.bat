@echo off
chcp 65001 >nul
echo ============================================
echo    法律文库系统 - 一键部署脚本
echo ============================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [错误] 请以管理员身份运行此脚本！
    pause
    exit /b 1
)

echo [步骤1/4] 导入 Docker 镜像...
docker load -i law_images.tar
if %errorLevel% neq 0 (
    echo [错误] 导入镜像失败！
    pause
    exit /b 1
)
echo [完成] 镜像导入成功！
echo.

echo [步骤2/4] 启动后端和数据库服务...
docker-compose up -d
if %errorLevel% neq 0 (
    echo [错误] 启动服务失败！
    pause
    exit /b 1
)
echo [完成] 服务启动成功！
echo.

echo [步骤3/4] 等待 MongoDB 就绪...
timeout /t 10 /nobreak >nul
echo [完成] MongoDB 已就绪！
echo.

echo [步骤4/4] 恢复数据库数据...
docker cp mongodump\law_system law_system_mongodb:/tmp/law_system
docker exec law_system_mongodb mongorestore --db law_system /tmp/law_system
if %errorLevel% neq 0 (
    echo [警告] 数据恢复可能有问题，请检查！
) else (
    echo [完成] 数据恢复成功！
)
echo.

echo ============================================
echo    部署完成！
echo ============================================
echo.
echo 后端服务地址: http://localhost:4008
echo MongoDB 端口: 27019
echo.
echo 请配置 Nginx 反向代理到 4008 端口
echo 前端静态文件请复制到 D:\Nginx_law 目录
echo.
pause
