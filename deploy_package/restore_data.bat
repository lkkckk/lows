@echo off
chcp 65001 >nul
echo ========================================
echo   法律检索系统 - 数据恢复脚本
echo ========================================
echo.

set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%

if not exist "mongodb_dump\law_system" (
    echo 错误：未找到数据库备份文件夹 mongodb_dump\law_system
    pause
    exit /b
)

echo 正在恢复数据库数据...
docker run --rm -v %SCRIPT_DIR%mongodb_dump:/backup -v deploy_package_law_system_db_data:/data/db --network deploy_package_law_system_network mongo:5.0 mongorestore --drop --db law_system /backup/law_system --host mongodb

echo.
echo ========================================
echo   数据恢复完成！
echo   共恢复 38 部法规，3530 条条文
echo ========================================
echo.
pause
