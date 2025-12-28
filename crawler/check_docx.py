from docx import Document

# 读取 Word 文档
file_path = "manual_data/公安机关办理行政案件程序规定.docx"
doc = Document(file_path)

# 提取所有段落的原始文本
paragraphs = [para.text for para in doc.paragraphs]

# 扫描包含关键字的段落
print("搜索包含关键日期/机关信息的段落：\n")
for i, para in enumerate(paragraphs):
    if any(kw in para for kw in ["发布", "施行", "生效", "2018", "2019", "2020", "2021", "公安部令", "第160号"]):
        print(f"[{i}] {repr(para)}\n")
