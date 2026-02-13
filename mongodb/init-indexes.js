// MongoDB 初始化脚本 - 创建索引

// 切换到目标数据库
db = db.getSiblingDB('law_system');

print('开始创建索引...');

// ==================== laws 集合索引 ====================
print('创建 laws 集合索引...');

// 1. 唯一索引：law_id
db.laws.createIndex(
  { "law_id": 1 },
  { unique: true, name: "idx_law_id_unique" }
);

// 2. 复合索引：分类 + 效力层级 + 状态（用于筛选）
db.laws.createIndex(
  { "category": 1, "level": 1, "status": 1 },
  { name: "idx_category_level_status" }
);

// 3. 文本索引：标题 + 摘要 + 全文（用于全局搜索）
db.laws.createIndex(
  {
    "title": "text",
    "summary": "text",
    "full_text": "text"
  },
  {
    default_language: "none",  // 禁用语言特定处理（避免英文词干）
    weights: {
      "title": 10,      // 标题权重最高
      "summary": 5,     // 摘要次之
      "full_text": 1    // 全文权重最低
    },
    name: "idx_text_search"
  }
);

// 4. 单字段索引：标签（用于标签筛选）
db.laws.createIndex(
  { "tags": 1 },
  { name: "idx_tags" }
);

// 5. 单字段索引：生效日期（用于时间范围查询）
db.laws.createIndex(
  { "effect_date": -1 },
  { name: "idx_effect_date_desc" }
);

print('laws 集合索引创建完成');

// ==================== law_articles 集合索引 ====================
print('创建 law_articles 集合索引...');

// 1. 复合索引：law_id + article_num（用于精准定位条文）
db.law_articles.createIndex(
  { "law_id": 1, "article_num": 1 },
  { unique: true, name: "idx_law_article_unique" }
);

// 2. 单字段索引：law_id（用于获取某法规的所有条文）
db.law_articles.createIndex(
  { "law_id": 1 },
  { name: "idx_law_id" }
);

// 3. 文本索引：条文内容 + 条号显示（用于条文内搜索）
db.law_articles.createIndex(
  {
    "content": "text",
    "article_display": "text",
    "keywords": "text"
  },
  {
    default_language: "none",
    weights: {
      "keywords": 15,        // 关键词权重最高
      "article_display": 10,
      "content": 5
    },
    name: "idx_article_text_search"
  }
);

// 4. 复合索引：章节 + 条号（用于按章节浏览）
db.law_articles.createIndex(
  { "law_id": 1, "chapter": 1, "article_num": 1 },
  { name: "idx_chapter_article" }
);

print('law_articles 集合索引创建完成');

// ==================== doc_templates 集合索引 ====================
print('创建 doc_templates 集合索引...');

// 1. 唯一索引：template_id
db.doc_templates.createIndex(
  { "template_id": 1 },
  { unique: true, name: "idx_template_id_unique" }
);

// 2. 单字段索引：分类（用于分类筛选）
db.doc_templates.createIndex(
  { "category": 1 },
  { name: "idx_template_category" }
);

// 3. 文本索引：模板名称（用于搜索）
db.doc_templates.createIndex(
  { "name": "text" },
  { default_language: "none", name: "idx_template_name_search" }
);

print('doc_templates 集合索引创建完成');

// ==================== doc_instances 集合索引 ====================
print('创建 doc_instances 集合索引...');

// 1. 单字段索引：template_id（用于查询某模板的所有实例）
db.doc_instances.createIndex(
  { "template_id": 1 },
  { name: "idx_doc_template_id" }
);

// 2. 单字段索引：创建时间（用于时间排序）
db.doc_instances.createIndex(
  { "created_at": -1 },
  { name: "idx_doc_created_at_desc" }
);

// 3. 单字段索引：创建人（用于个人文书查询）
db.doc_instances.createIndex(
  { "created_by": 1 },
  { name: "idx_doc_created_by" }
);

print('doc_instances 集合索引创建完成');

// ==================== 验证索引创建 ====================
print('\n========== 索引创建总结 ==========');

print('\nlaws 集合索引:');
printjson(db.laws.getIndexes());

print('\nlaw_articles 集合索引:');
printjson(db.law_articles.getIndexes());

print('\ndoc_templates 集合索引:');
printjson(db.doc_templates.getIndexes());

print('\ndoc_instances 集合索引:');
printjson(db.doc_instances.getIndexes());

// ==================== cases 集合索引 ====================
print('\n创建 cases 集合索引...');

db.cases.createIndex(
  { "case_id": 1 },
  { unique: true, name: "idx_case_id" }
);

db.cases.createIndex(
  { "status": 1, "created_at": -1 },
  { name: "idx_case_status_date" }
);

db.cases.createIndex(
  { "case_type": 1 },
  { name: "idx_case_type" }
);

db.cases.createIndex(
  { "case_name": "text", "description": "text", "tags": "text" },
  { name: "idx_case_text", default_language: "none" }
);

print('cases 集合索引创建完成');

// ==================== transcripts 集合索引 ====================
print('创建 transcripts 集合索引...');

db.transcripts.createIndex(
  { "transcript_id": 1 },
  { unique: true, name: "idx_transcript_id" }
);

db.transcripts.createIndex(
  { "case_id": 1, "created_at": -1 },
  { name: "idx_transcript_case_date" }
);

db.transcripts.createIndex(
  { "analysis_status": 1 },
  { name: "idx_analysis_status" }
);

db.transcripts.createIndex(
  { "type": 1 },
  { name: "idx_transcript_type" }
);

db.transcripts.createIndex(
  { "subject_role": 1 },
  { name: "idx_subject_role" }
);

db.transcripts.createIndex(
  { "content": "text", "keywords": "text" },
  { name: "idx_transcript_text", default_language: "none" }
);

print('transcripts 集合索引创建完成');

print('\ncases 集合索引:');
printjson(db.cases.getIndexes());

print('\ntranscripts 集合索引:');
printjson(db.transcripts.getIndexes());

print('\n所有索引创建完成！');
