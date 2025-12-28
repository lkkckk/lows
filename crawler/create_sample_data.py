"""
创建示例数据（用于测试）
"""
import json
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# 示例法规数据
sample_laws = [
    {
        "law_id": "criminal_procedure_law_2018",
        "title": "中华人民共和国刑事诉讼法",
        "category": "刑事法律",
        "level": "法律",
        "issue_org": "全国人民代表大会",
        "issue_date": "2018-10-26",
        "effect_date": "2019-01-01",
        "status": "有效",
        "summary": "规范刑事诉讼程序的基本法律",
        "tags": ["刑事", "诉讼", "程序法"],
        "source_url": "https://example.com/law/1",
        "full_text": "第一编 总则\n第一章 任务和基本原则\n第一条 为了保证刑法的正确实施...",
        "created_at": datetime.utcnow().isoformat(),
    },
    {
        "law_id": "public_security_admin_law_2012",
        "title": "中华人民共和国治安管理处罚法",
        "category": "行政法律",
        "level": "法律",
        "issue_org": "全国人民代表大会常务委员会",
        "issue_date": "2012-10-26",
        "effect_date": "2013-01-01",
        "status": "有效",
        "summary": "维护社会治安秩序，保障公共安全",
        "tags": ["治安", "行政处罚", "公共安全"],
        "source_url": "https://example.com/law/2",
        "full_text": "第一章 总则\n第一条 为维护社会治安秩序...",
        "created_at": datetime.utcnow().isoformat(),
    },
]

# 示例条文数据
sample_articles = [
    {
        "law_id": "criminal_procedure_law_2018",
        "article_num": 1,
        "article_display": "第一条",
        "chapter": "第一编 总则",
        "section": "第一章 任务和基本原则",
        "content": "为了保证刑法的正确实施，惩罚犯罪，保护人民，保障国家安全和社会公共安全，维护社会主义社会秩序，根据宪法，制定本法。",
        "keywords": ["刑法", "惩罚犯罪", "保护人民", "国家安全"],
        "created_at": datetime.utcnow().isoformat(),
    },
    {
        "law_id": "criminal_procedure_law_2018",
        "article_num": 83,
        "article_display": "第八十三条",
        "chapter": "第二编 侦查",
        "section": "第四章 强制措施",
        "content": "公安机关拘留人的时候，必须出示拘留证。拘留后，应当立即将被拘留人送看守所羁押，至迟不得超过二十四小时。除无法通知或者涉嫌危害国家安全犯罪、恐怖活动犯罪通知可能有碍侦查的情形以外，应当在拘留后二十四小时以内，通知被拘留人的家属。",
        "keywords": ["拘留", "拘留证", "看守所", "家属通知", "强制措施"],
        "created_at": datetime.utcnow().isoformat(),
    },
    {
        "law_id": "public_security_admin_law_2012",
        "article_num": 1,
        "article_display": "第一条",
        "chapter": "第一章 总则",
        "section": None,
        "content": "为维护社会治安秩序，保障公共安全，保护公民、法人和其他组织的合法权益，规范和保障公安机关及其人民警察依法履行治安管理职责，制定本法。",
        "keywords": ["社会治安", "公共安全", "治安管理", "公安机关"],
        "created_at": datetime.utcnow().isoformat(),
    },
    {
        "law_id": "public_security_admin_law_2012",
        "article_num": 10,
        "article_display": "第十条",
        "chapter": "第一章 总则",
        "section": None,
        "content": "治安管理处罚的种类分为：（一）警告；（二）罚款；（三）行政拘留；（四）吊销公安机关发放的许可证。对违反治安管理的外国人，可以附加适用限期出境或者驱逐出境。",
        "keywords": ["处罚种类", "警告", "罚款", "行政拘留", "驱逐出境"],
        "created_at": datetime.utcnow().isoformat(),
    },
]

# 示例文书模板
sample_templates = [
    {
        "template_id": "arrest_warrant",
        "name": "拘留证",
        "category": "刑事办案",
        "fields": [
            {
                "name": "suspect_name",
                "label": "犯罪嫌疑人姓名",
                "type": "text",
                "required": True,
            },
            {
                "name": "suspect_gender",
                "label": "性别",
                "type": "text",
                "required": True,
            },
            {
                "name": "suspect_age",
                "label": "年龄",
                "type": "text",
                "required": True,
            },
            {
                "name": "suspect_id",
                "label": "身份证号",
                "type": "text",
                "required": True,
            },
            {
                "name": "case_reason",
                "label": "案由",
                "type": "textarea",
                "required": True,
            },
            {
                "name": "police_name",
                "label": "办案民警",
                "type": "text",
                "required": True,
            },
            {
                "name": "date",
                "label": "日期",
                "type": "date",
                "required": True,
            },
        ],
        "content": """拘留证

兹因 {{suspect_name}}（性别：{{suspect_gender}}，年龄：{{suspect_age}}岁，身份证号：{{suspect_id}}）涉嫌 {{case_reason}}，根据《中华人民共和国刑事诉讼法》第八十三条之规定，经审查决定对其采取拘留措施。

现依法出示本拘留证，并将被拘留人送看守所羁押。

特此证明。

办案民警：{{police_name}}
日期：{{date}}

（公安机关印章）
""",
        "created_at": datetime.utcnow().isoformat(),
    },
]

# 写入文件
print("📝 正在生成示例数据...")

# 法规数据
laws_file = OUTPUT_DIR / "laws.jsonl"
with open(laws_file, "w", encoding="utf-8") as f:
    for law in sample_laws:
        f.write(json.dumps(law, ensure_ascii=False) + "\n")
print(f"✅ 已生成 {len(sample_laws)} 条法规数据: {laws_file}")

# 条文数据
articles_file = OUTPUT_DIR / "law_articles.jsonl"
with open(articles_file, "w", encoding="utf-8") as f:
    for article in sample_articles:
        f.write(json.dumps(article, ensure_ascii=False) + "\n")
print(f"✅ 已生成 {len(sample_articles)} 条条文数据: {articles_file}")

# 模板数据（可选，需要单独导入到 doc_templates 集合）
templates_file = OUTPUT_DIR / "doc_templates.jsonl"
with open(templates_file, "w", encoding="utf-8") as f:
    for template in sample_templates:
        f.write(json.dumps(template, ensure_ascii=False) + "\n")
print(f"✅ 已生成 {len(sample_templates)} 个文书模板: {templates_file}")

print("\n🎉 示例数据生成完成！")
print(f"\n下一步：运行 python import_data.py 导入数据到 MongoDB")
