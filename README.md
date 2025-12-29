# 警务法规离线查询系统

## 📖 项目简介

这是一个专为公安机关设计的离线法律法规查询系统，支持局域网部署，提供法规检索、条文精准定位、文书模板管理等功能。

### 核心特性

- ✅ **离线部署**：支持完全离线运行，无需外网依赖
- 🔍 **智能检索**：支持全文搜索、条号定位、关键字高亮
- 📄 **文书模板**：内置常用文书模板，支持变量填充与 PDF 导出
- 🚀 **高性能**：基于 MongoDB 索引优化，毫秒级响应
- 🐳 **容器化**：Docker Compose 一键部署

## 🏗️ 技术架构

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   React     │─────▶│   FastAPI    │─────▶│  MongoDB    │
│   前端应用   │      │   后端 API    │      │   数据库     │
└─────────────┘      └──────────────┘      └─────────────┘
                             ▲
                             │
                     ┌───────┴────────┐
                     │  Python 爬虫   │
                     │  数据采集工具   │
                     └────────────────┘
```

### 技术栈

- **前端**：React 18 + Vite + TailwindCSS + Ant Design
- **后端**：FastAPI + Motor (异步 MongoDB 驱动)
- **数据库**：MongoDB 5.0+
- **爬虫**：Python 3.10+ + BeautifulSoup4 + httpx
- **文档导出**：WeasyPrint (HTML to PDF)
- **部署**：Docker + Docker Compose

## 📦 项目结构

```
law-query-system/
├── backend/                 # 后端 FastAPI 服务
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   ├── db.py           # 数据库连接
│   │   └── main.py         # 应用入口
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # 前端 React 应用
│   ├── src/
│   │   ├── components/    # React 组件
│   │   ├── pages/         # 页面组件
│   │   ├── services/      # API 调用
│   │   └── App.jsx
│   ├── package.json
│   └── Dockerfile
├── crawler/                # 爬虫与数据导入工具
│   ├── spiders/           # 爬虫适配器
│   ├── pipeline.py        # 数据清洗管道
│   ├── import_data.py     # MongoDB 导入脚本
│   └── requirements.txt
├── mongodb/                # MongoDB 初始化脚本
│   └── init-indexes.js    # 索引创建脚本
├── docker-compose.yml      # Docker 编排文件
└── README.md
```

## 🚀 快速开始

### 前置要求

- Docker Desktop (Windows)
- Python 3.10+
- Node.js 18+

### 1. 启动 MongoDB

```powershell
cd law-query-system
docker-compose up -d mongodb
```

等待 MongoDB 启动完成（约 10 秒）。

### 2. 爬取法规数据（联网环境）

```powershell
cd crawler
pip install -r requirements.txt
python run_crawler.py
```

这将生成：
- `output/laws.jsonl` - 法规元信息
- `output/law_articles.jsonl` - 条文数据

### 3. 导入数据到 MongoDB

```powershell
python import_data.py
```

### 4. 启动后端服务

方式一：Docker（推荐）
```powershell
docker-compose up -d backend
```

方式二：本地开发
```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 4008 --reload
```

后端服务地址：http://localhost:4008
API 文档：http://localhost:4008/docs

### 5. 启动前端应用

方式一：Docker
```powershell
docker-compose up -d frontend
```

方式二：本地开发
```powershell
cd frontend
npm install
npm run dev
```

前端访问地址：http://localhost:6011

## 📚 MongoDB 数据模型

### 集合：laws (法规元信息)

```json
{
  "_id": "ObjectId",
  "law_id": "unique_law_code",
  "title": "中华人民共和国刑事诉讼法",
  "category": "刑事法律",
  "level": "法律",
  "issue_org": "全国人民代表大会",
  "issue_date": "2018-10-26",
  "effect_date": "2019-01-01",
  "status": "有效",
  "summary": "规范刑事诉讼程序...",
  "tags": ["刑事", "诉讼"],
  "source_url": "http://example.com/law/123",
  "full_text": "完整法规正文...",
  "created_at": "2025-12-26T10:00:00Z"
}
```

### 集合：law_articles (条文)

```json
{
  "_id": "ObjectId",
  "law_id": "unique_law_code",
  "article_num": 83,
  "article_display": "第八十三条",
  "chapter": "第二编 侦查",
  "section": "第四章 强制措施",
  "content": "公安机关拘留人的时候，必须出示拘留证...",
  "keywords": ["拘留", "拘留证", "强制措施"],
  "created_at": "2025-12-26T10:00:00Z"
}
```

### 集合：doc_templates (文书模板)

```json
{
  "_id": "ObjectId",
  "template_id": "arrest_warrant",
  "name": "拘留证",
  "category": "刑事办案",
  "fields": [
    {"name": "suspect_name", "label": "犯罪嫌疑人姓名", "type": "text"},
    {"name": "suspect_gender", "label": "性别", "type": "select", "options": ["男", "女"]},
    {"name": "case_reason", "label": "案由", "type": "text"}
  ],
  "content": "兹因{{suspect_name}}涉嫌{{case_reason}}...",
  "created_at": "2025-12-26T10:00:00Z"
}
```

## 🔍 核心功能说明

### 1. 条号智能识别

支持多种输入格式：
- "第八十三条" → 跳转到第 83 条
- "83条" → 跳转到第 83 条
- "83" → 跳转到第 83 条

实现原理：
```javascript
function parseArticleNumber(input) {
  // 中文数字转换
  const chineseMap = {'一': 1, '二': 2, '三': 3, ...};
  
  // 正则匹配
  const patterns = [
    /第([零一二三四五六七八九十百]+)条/,
    /(\d+)条/,
    /^(\d+)$/
  ];
  
  // 返回条号
  return articleNumber;
}
```

### 2. 全文检索方案

#### MongoDB Text Index（基础方案）

```javascript
// 创建文本索引
db.law_articles.createIndex({
  "content": "text",
  "article_display": "text"
}, {
  default_language: "none",  // 禁用英文词干提取
  weights: {
    "content": 10,
    "article_display": 5
  }
});

// 查询示例
db.law_articles.find({
  $text: { $search: "拘留 传唤" }
});
```

**局限性**：
- 中文分词较弱（单字分词）
- 不支持拼音搜索
- 相关性评分简单

#### 升级方案（可选）

使用 Elasticsearch/OpenSearch：
- 支持 IK 中文分词器
- 更强的相关性算法
- 拼音搜索支持

### 3. 文书 PDF 导出

使用 WeasyPrint 将 HTML 转 PDF：

```python
from weasyprint import HTML

def export_to_pdf(template_html: str) -> bytes:
    html = HTML(string=template_html)
    return html.write_pdf()
```

支持：
- 自定义样式（CSS）
- 页眉页脚
- 水印
- 分页控制

## 🔧 环境变量配置

创建 `.env` 文件：

```env
# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=law_system

# Backend
BACKEND_PORT=4008
CORS_ORIGINS=http://localhost:6011

# Frontend
VITE_API_URL=http://localhost:4008/api
```

## 🐛 常见问题

### Q1: MongoDB 连接失败

```
检查 Docker 容器状态：
docker-compose ps

重启 MongoDB：
docker-compose restart mongodb
```

### Q2: 中文检索结果不准确

**解决方案**：
1. 使用 `$regex` 正则查询（小数据量）
2. 升级到 Elasticsearch（大数据量）

### Q3: PDF 导出中文乱码

确保安装中文字体：
```dockerfile
RUN apt-get update && apt-get install -y fonts-noto-cjk
```

## 📈 性能优化建议

1. **MongoDB 索引优化**
   - 为常用查询字段创建复合索引
   - 定期执行 `db.collection.stats()` 检查索引使用率

2. **前端虚拟列表**
   - 使用 `react-window` 渲染长列表
   - 避免一次性渲染数千条法规条文

3. **API 缓存**
   - 使用 Redis 缓存热点法规
   - 设置合理的 TTL

4. **静态资源 CDN**
   - Nginx 启用 gzip 压缩
   - 设置浏览器缓存策略

## 📝 开发计划

- [x] 基础架构搭建
- [x] MongoDB 数据模型设计
- [x] 后端 API 实现
- [x] 前端页面开发
- [x] 爬虫框架
- [ ] 单元测试
- [ ] 性能压测
- [ ] 用户手册

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目仅供内部使用，未经授权不得外传。

## 📞 联系方式

技术支持：xxx@police.gov.cn

---

**⚠️ 重要提示**：本系统涉及警务数据，请严格遵守保密规定，禁止在公网部署。
