@echo off
chcp 65001 >nul
echo ========================================
echo   法律检索系统 - 生产环境全新部署脚本
echo ========================================
echo.

set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%

echo [1/5] 正在加载 MongoDB 镜像...
if not exist "mongo_image.tar" (
    echo 错误：未找到 mongo_image.tar
    pause
    exit /b
)
docker load -i mongo_image.tar
echo MongoDB 镜像加载成功！

echo [2/5] 正在加载后端镜像...
if not exist "backend_image.tar" (
    echo 错误：未找到 backend_image.tar
    pause
    exit /b
)
docker load -i backend_image.tar
echo 后端镜像加载成功！

echo [3/5] 正在清理旧容器...
docker stop law_system_backend 2>nul
docker stop law_system_mongodb 2>nul
docker rm -f law_system_backend 2>nul
docker rm -f law_system_mongodb 2>nul

echo [4/5] 正在启动服务...
docker-compose up -d
if %errorlevel% neq 0 (
    echo 错误：docker-compose 启动失败。
    pause
    exit /b
)
echo 等待数据库启动 (10秒)...
timeout /t 10 /nobreak >nul

echo [5/5] 正在恢复数据库数据...
if not exist "mongodb_dump\law_system" (
    echo 警告：未找到数据库备份，跳过数据恢复。
    goto :done
)
docker cp "mongodb_dump\law_system" law_system_mongodb:/restore/law_system
docker exec law_system_mongodb mongorestore --drop --db law_system /restore/law_system
docker exec law_system_mongodb rm -rf /restore

:done
echo.
echo ========================================
echo   部署完成！
echo   后端地址: http://localhost:4008
echo   MongoDB: localhost:27019
echo ========================================
echo.
pause
