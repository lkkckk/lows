# 警务法规查询系统 - 快速启动脚本
# 适用于 Windows PowerShell

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   警务法规查询系统 - 快速启动" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Docker 是否运行
Write-Host "[1/5] 检查 Docker..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "✅ Docker 正在运行" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker 未运行，请先启动 Docker Desktop" -ForegroundColor Red
    exit 1
}

# 启动 MongoDB
Write-Host ""
Write-Host "[2/5] 启动 MongoDB..." -ForegroundColor Yellow
docker-compose up -d mongodb
Start-Sleep -Seconds 10
Write-Host "✅ MongoDB 已启动" -ForegroundColor Green

# 检查是否需要导入示例数据
Write-Host ""
Write-Host "[3/5] 检查数据..." -ForegroundColor Yellow
$dataFiles = @(
    "crawler\output\laws.jsonl",
    "crawler\output\law_articles.jsonl"
)

$hasData = $true
foreach ($file in $dataFiles) {
    if (-not (Test-Path $file)) {
        $hasData = $false
        break
    }
}

if (-not $hasData) {
    Write-Host "⚠️  未检测到数据文件，正在生成示例数据..." -ForegroundColor Yellow
    Push-Location crawler
    python create_sample_data.py
    Pop-Location
    Write-Host "✅ 示例数据已生成" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "正在导入数据到 MongoDB..." -ForegroundColor Yellow
    Push-Location crawler
    python import_data.py
    Pop-Location
    Write-Host "✅ 数据导入完成" -ForegroundColor Green
} else {
    Write-Host "✅ 数据文件已存在" -ForegroundColor Green
}

# 启动后端
Write-Host ""
Write-Host "[4/5] 启动后端服务..." -ForegroundColor Yellow
docker-compose up -d backend
Start-Sleep -Seconds 5
Write-Host "✅ 后端服务已启动" -ForegroundColor Green

# 启动前端
Write-Host ""
Write-Host "[5/5] 启动前端应用..." -ForegroundColor Yellow
Write-Host "提示：首次启动需要安装依赖，可能需要几分钟..." -ForegroundColor Cyan

Push-Location frontend
if (-not (Test-Path "node_modules")) {
    Write-Host "安装前端依赖..." -ForegroundColor Yellow
    npm install --registry=https://registry.npmmirror.com
}
Pop-Location

docker-compose up -d frontend
Write-Host "✅ 前端应用已启动" -ForegroundColor Green

# 等待服务完全启动
Write-Host ""
Write-Host "等待服务完全启动..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# 显示访问信息
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   🎉 系统启动完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📱 前端应用: http://localhost:5173" -ForegroundColor Green
Write-Host "🔧 后端 API: http://localhost:8000" -ForegroundColor Green
Write-Host "📖 API 文档: http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "提示：" -ForegroundColor Yellow
Write-Host "- 停止服务：docker-compose down" -ForegroundColor Gray
Write-Host "- 查看日志：docker-compose logs [service_name]" -ForegroundColor Gray
Write-Host "- 重启服务：docker-compose restart [service_name]" -ForegroundColor Gray
Write-Host ""

# 询问是否打开浏览器
$openBrowser = Read-Host "是否在浏览器中打开应用？(y/n)"
if ($openBrowser -eq "y") {
    Start-Process "http://localhost:5173"
}

Write-Host ""
Write-Host "祝使用愉快！ 🚀" -ForegroundColor Cyan
