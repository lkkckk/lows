# API 接口设计文档

## 📋 目录

- [通用说明](#通用说明)
- [法规相关 API](#法规相关-api)
- [文书模板相关 API](#文书模板相关-api)
- [错误码说明](#错误码说明)

---

## 通用说明

### 基础 URL

```
开发环境: http://localhost:4008/api
生产环境: https://your-domain.com/api
```

### 统一响应格式

所有 API 返回格式统一为：

```json
{
  "success": true,
  "data": {...},
  "pagination": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  },
  "error": null
}
```

### 分页参数

所有列表接口支持以下分页参数：

- `page`: 页码（从 1 开始）
- `page_size`: 每页大小（默认 20，最大 100）

---

## 法规相关 API

### 1. 获取法规列表

**接口**: `GET /laws/`

**查询参数**:
- `page`: 页码
- `page_size`: 每页大小
- `category`: 法规分类（可选）
- `level`: 效力层级（可选）
- `status`: 效力状态（可选）
- `tags`: 标签，逗号分隔（可选）

**请求示例**:
```
GET /laws/?page=1&page_size=20&category=刑事法律&level=法律
```

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "law_id": "criminal_procedure_law_2018",
      "title": "中华人民共和国刑事诉讼法",
      "category": "刑事法律",
      "level": "法律",
      "issue_date": "2018-10-26",
      "effect_date": "2019-01-01",
      "status": "有效",
      "tags": ["刑事", "诉讼"]
    }
  ],
  "pagination": {
    "total": 50,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  }
}
```

---

### 2. 获取法规详情

**接口**: `GET /laws/{law_id}`

**路径参数**:
- `law_id`: 法规唯一标识

**响应示例**:
```json
{
  "success": true,
  "data": {
    "law_id": "criminal_procedure_law_2018",
    "title": "中华人民共和国刑事诉讼法",
    "category": "刑事法律",
    "level": "法律",
    "issue_org": "全国人民代表大会",
    "issue_date": "2018-10-26",
    "effect_date": "2019-01-01",
    "status": "有效",
    "summary": "规范刑事诉讼程序的基本法律",
    "tags": ["刑事", "诉讼"],
    "full_text": "第一编 总则\n第一章..."
  }
}
```

---

### 3. 获取法规条文列表

**接口**: `GET /laws/{law_id}/articles`

**查询参数**:
- `chapter`: 章节筛选（可选）

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "law_id": "criminal_procedure_law_2018",
      "article_num": 83,
      "article_display": "第八十三条",
      "chapter": "第二编 侦查",
      "section": "第四章 强制措施",
      "content": "公安机关拘留人的时候，必须出示拘留证...",
      "keywords": ["拘留", "拘留证"]
    }
  ]
}
```

---

### 4. 根据条号获取条文

**接口**: `GET /laws/{law_id}/articles/{article_num}`

**路径参数**:
- `law_id`: 法规 ID
- `article_num`: 条号（数字）

**响应示例**:
```json
{
  "success": true,
  "data": {
    "law_id": "criminal_procedure_law_2018",
    "article_num": 83,
    "article_display": "第八十三条",
    "content": "公安机关拘留人的时候..."
  }
}
```

---

### 5. 在单个法规内搜索

**接口**: `POST /laws/{law_id}/search`

**请求体**:
```json
{
  "query": "拘留",
  "page": 1,
  "page_size": 20
}
```

**功能说明**:
- 支持条号搜索：输入"第八十三条"、"83条"、"83"等
- 支持关键字搜索：输入"拘留"、"传唤"等

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "law_id": "criminal_procedure_law_2018",
      "article_num": 83,
      "article_display": "第八十三条",
      "content": "公安机关拘留人的时候...",
      "highlight": "...必须出示拘留证...",
      "score": 2.5
    }
  ],
  "pagination": {
    "total": 5,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
}
```

---

### 6. 全库搜索

**接口**: `POST /laws/search`

**请求体**:
```json
{
  "query": "拘留",
  "page": 1,
  "page_size": 20
}
```

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "law_id": "criminal_procedure_law_2018",
      "law_title": "中华人民共和国刑事诉讼法",
      "article_num": 83,
      "article_display": "第八十三条",
      "content": "公安机关拘留人的时候...",
      "highlight": "...必须出示拘留证...",
      "score": 3.2
    }
  ],
  "pagination": {...}
}
```

---

### 7. 获取法规分类列表

**接口**: `GET /laws/meta/categories`

**响应示例**:
```json
{
  "success": true,
  "data": ["刑事法律", "行政法律", "民事法律"]
}
```

---

### 8. 获取效力层级列表

**接口**: `GET /laws/meta/levels`

**响应示例**:
```json
{
  "success": true,
  "data": ["法律", "行政法规", "部门规章", "地方性法规"]
}
```

---

## 文书模板相关 API

### 1. 获取模板列表

**接口**: `GET /templates/`

**查询参数**:
- `page`: 页码
- `page_size`: 每页大小
- `category`: 模板分类（可选）

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "template_id": "arrest_warrant",
      "name": "拘留证",
      "category": "刑事办案",
      "fields": [
        {
          "name": "suspect_name",
          "label": "犯罪嫌疑人姓名",
          "type": "text",
          "required": true
        }
      ],
      "created_at": "2025-12-26T10:00:00Z"
    }
  ]
}
```

---

### 2. 获取模板详情

**接口**: `GET /templates/{template_id}`

**响应示例**:
```json
{
  "success": true,
  "data": {
    "template_id": "arrest_warrant",
    "name": "拘留证",
    "category": "刑事办案",
    "fields": [...],
    "content": "拘留证\n\n兹因{{suspect_name}}..."
  }
}
```

---

### 3. 渲染模板（预览）

**接口**: `POST /templates/{template_id}/render`

**请求体**:
```json
{
  "suspect_name": "张三",
  "suspect_gender": "男",
  "case_reason": "盗窃"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "content": "拘留证\n\n兹因张三（性别：男）涉嫌盗窃..."
  }
}
```

---

### 4. 导出为 PDF

**接口**: `POST /templates/{template_id}/export/pdf`

**请求体**: 同"渲染模板"

**响应**: 二进制文件流（application/pdf）

**使用示例（JavaScript）**:
```javascript
const response = await fetch('/api/templates/arrest_warrant/export/pdf', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ suspect_name: '张三', ... })
});

const blob = await response.blob();
const url = window.URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = '拘留证.pdf';
a.click();
```

---

### 5. 导出为 DOCX

**接口**: `POST /templates/{template_id}/export/docx`

**请求/响应**: 同"导出为 PDF"，MIME 类型为 `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

---

## 错误码说明

### HTTP 状态码

- `200`: 请求成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

### 错误响应格式

```json
{
  "success": false,
  "data": null,
  "error": "法规不存在"
}
```

### 常见错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| 法规不存在 | law_id 不正确 | 检查 law_id 是否正确 |
| 模板不存在 | template_id 不正确 | 检查 template_id 是否正确 |
| 请求参数错误 | 缺少必填参数 | 补充缺失的参数 |
| 搜索失败 | 服务异常 | 稍后重试或联系管理员 |

---

## 测试工具

推荐使用以下工具测试 API：

1. **Swagger UI**（内置）: http://localhost:4008/docs
2. **Postman**: 导入 OpenAPI 规范
3. **cURL**: 命令行测试

**cURL 示例**:
```bash
# 获取法规列表
curl "http://localhost:4008/api/laws/?page=1&page_size=20"

# 全局搜索
curl -X POST "http://localhost:4008/api/laws/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"拘留","page":1,"page_size":20}'
```

---

**文档版本**: v1.0.0  
**更新日期**: 2025-12-26
