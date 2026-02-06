@echo off
chcp 65001
echo =======================================================
echo     准备离线向量搜索服务镜像 (Development -> Production)
echo =======================================================
echo.

cd /d %~dp0
cd backend

echo [1/4] 安装必要的 Python 库 (用于下载模型)...
pip install huggingface_hub -i https://mirrors.aliyun.com/pypi/simple/
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 安装依赖失败，请检查 Python 环境
    pause
    exit /b
)

echo.
echo [2/4] 从 HuggingFace 镜像站下载 BGE-M3 模型...
python scripts/download_model.py
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 模型下载失败
    pause
    exit /b
)

echo.
echo [3/4] 构建 Docker 镜像 law_system_embedding...
docker build -t law_system_embedding -f EmbeddingDockerfile .
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Docker 镜像构建失败，请确保 Docker Desktop 已运行
    pause
    exit /b
)

echo.
echo [4/4] 导出镜像为 embedding.tar (用于生产环境部署)...
docker save -o ../deploy_package/embedding.tar law_system_embedding
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 镜像导出失败
    pause
    exit /b
)
echo ✅ 镜像已保存至 deploy_package/embedding.tar (约2GB)

echo.
echo =======================================================
echo 🎉 准备完成！
echo 您现在可以将 deploy_package 文件夹复制到生产服务器。
echo =======================================================
pause
