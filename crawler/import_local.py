import os
import re
import hashlib
import json
import logging
from pymongo import MongoClient, ASCENDING, TEXT
from dotenv import load_dotenv

# Word 文档支持
try:
    from docx import Document
    DOCX_SUPPORTED = True
except ImportError:
    DOCX_SUPPORTED = False
    logging.warning("python-docx 未安装，.docx 文件将不被支持。运行: pip install python-docx")

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', '.env'))

class LocalImporter:
    def __init__(self, input_dir="manual_data"):
        self.input_dir = input_dir
        self.mongo_uri = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[os.getenv("MONGODB_DB", "law_system")]  # 确保数据库名与后端一致
        self.setup_indexes()

    def setup_indexes(self):
        """确保索引存在（忽略已存在的索引冲突）"""
        try:
            self.db.laws.create_index([("title", ASCENDING)], unique=True)
        except Exception:
            pass
        try:
            self.db.laws.create_index([("title", TEXT), ("summary", TEXT)], name="law_text_search")
        except Exception:
            pass
        try:
            self.db.law_articles.create_index([("law_id", ASCENDING), ("article_num", ASCENDING)], unique=True)
        except Exception:
            pass
        try:
            self.db.law_articles.create_index([("content", TEXT)], name="article_content_search")
        except Exception:
            pass

    def parse_metadata(self, content):
        """解析元数据和修订说明"""
        metadata = {
            "issue_date": "",
            "effect_date": "",
            "issue_org": "",  # 先留空，稍后兜底
            "status": "有效",
            "category": "",
            "level": "",  # 先留空，稍后兜底
            "summary": ""
        }
        
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        # 1. 尝试提取修订说明（圆括号包裹的长段落）
        # 通常在标题（第一行）之后，正文之前
        for i in range(1, min(10, len(lines))):
            line = lines[i]
            # 特征：以(或（开头，包含"通过"、"修正"、"修订"等字眼
            if (line.startswith('(') or line.startswith('（')) and \
               ('通过' in line or '修正' in line or '修订' in line):
                metadata['summary'] = line
                break
        
        # 2. 从前20行提取KV元数据
        header_lines = lines[:20]
        for line in header_lines:
            if "发布日期" in line or "公布日期" in line:
                metadata["issue_date"] = self._extract_value(line)
            if "实施日期" in line or "施行日期" in line:
                metadata["effect_date"] = self._extract_value(line)
            if "发布部门" in line or "发文机关" in line:
                metadata["issue_org"] = self._extract_value(line)
            if "效力" in line and ("级别" in line or "等级" in line):
                metadata["level"] = self._extract_value(line)
            if "类别" in line:
                metadata["category"] = self._extract_value(line)
        
        # 3. 从末尾解析结构化元数据（Word 文档常见格式）
        # 格式如：法规标题：xxx	法规文号：xxx
        #        发布日期：xxx	实施日期：xxx
        #        发布部门：xxx
        tail_lines = lines[-30:] if len(lines) > 30 else lines
        for line in tail_lines:
            # 排除无关内容
            if "资料提供" in line or "法律之星" in line or "引用时请对照正式文本" in line:
                continue
            if "扫码" in line or "查法规" in line:
                continue
            
            # 解析键值对（支持制表符分隔的多个键值对）
            # 例如：发布日期：2020年07月20日	实施日期：2020年09月01日
            pairs = re.split(r'\t+', line)
            for pair in pairs:
                pair = pair.strip()
                if not pair:
                    continue
                    
                if "法规标题" in pair:
                    val = self._extract_value(pair)
                    if val and not metadata.get("title_from_tail"):
                        metadata["title_from_tail"] = val
                elif "发布日期" in pair or "公布日期" in pair:
                    val = self._extract_value(pair)
                    if val and not metadata["issue_date"]:
                        metadata["issue_date"] = val
                elif "实施日期" in pair or "施行日期" in pair:
                    val = self._extract_value(pair)
                    if val and not metadata["effect_date"]:
                        metadata["effect_date"] = val
                elif "发布部门" in pair or "发文机关" in pair:
                    val = self._extract_value(pair)
                    if val and not metadata["issue_org"]:
                        metadata["issue_org"] = val
                elif "效力层级" in pair or "效力级别" in pair:
                    val = self._extract_value(pair)
                    if val and not metadata["level"]:
                        metadata["level"] = val

        # 4. 智能分类兜底
        title_for_category = metadata.get("title_from_tail") or lines[0] if lines else ""
        if not metadata["category"]:
            if "刑" in title_for_category or "罪" in title_for_category:
                metadata["category"] = "刑事法律"
            elif "治安" in title_for_category or "行政" in title_for_category:
                metadata["category"] = "行政法律"
            elif "程" in title_for_category and "定" in title_for_category:
                metadata["category"] = "程序规定"
            elif "规定" in title_for_category:
                metadata["category"] = "部门规章"
        
        # 5. 字段默认值兜底
        if not metadata["issue_org"]:
            # 根据标题智能判断发布机关
            if "公安" in title_for_category and "规定" in title_for_category:
                metadata["issue_org"] = "公安部"
            else:
                metadata["issue_org"] = "全国人民代表大会及其常务委员会"
        
        if not metadata["level"]:
            # 根据标题智能判断效力层级
            if "规定" in title_for_category or "办法" in title_for_category:
                metadata["level"] = "部门规章"
            else:
                metadata["level"] = "法律"
        
        return metadata

    def _extract_value(self, line):
        """提取冒号后的值"""
        # 支持中文冒号和英文冒号
        val = line.split('：')[-1].strip().split(':')[-1].strip()
        # 清理可能的制表符和多余空格
        val = re.sub(r'[\t\s]+$', '', val)
        return val

    def split_articles(self, full_text):
        """
        高级拆分逻辑：
        1. 识别并剥离 条文内容 中的 章节标题
        2. 维护准确的章节层级
        """
        articles = []
        
        # 预处理：统一全角空格
        full_text = re.sub(r'\u3000', ' ', full_text)
        
        # 预处理：移除无关内容
        lines_to_remove = [
            r'资料提供.*法律之星.*',
            r'引用时请对照正式文本',
            r'扫码随时查法规',
            r'法规标题：.*',
            r'法规文号：.*',
            r'发布日期：.*',
            r'实施日期：.*',
            r'发布部门：.*',
        ]
        for pattern in lines_to_remove:
            full_text = re.sub(pattern, '', full_text)
        
        # 核心正则：匹配 "第X条"
        # 使用 Lookahead 确保我们不消耗掉下一个条文的开始
        # 但 Python re 不支持变长 lookbehind，所以我们还是用迭代查找
        article_pattern = re.compile(r'(^|\n)\s*(第[零一二三四五六七八九十百千0-9]+条)\s+')
        
        matches = list(article_pattern.finditer(full_text))
        
        if not matches:
             # 尝试匹配无空格版
             article_pattern = re.compile(r'(^|\n)\s*(第[零一二三四五六七八九十百千0-9]+条)')
             matches = list(article_pattern.finditer(full_text))

        if not matches:
            logging.warning("  ⚠️ 未识别到标准条文格式")
            return [{
                "article_num": 1,
                "article_display": "全文",
                "content": full_text.strip(),
                "section": "",
                "chapter": ""
            }]

        # 分别匹配：编、章、节、以及特殊章节名（支持全角空格 \u3000 和普通空格）
        part_pattern = re.compile(r'^\s*(第[零一二三四五六七八九十百千]+编[\s\u3000]+.*)$')  # 第X编
        chapter_pattern = re.compile(r'^\s*(第[零一二三四五六七八九十百千]+章[\s\u3000]+.*)$')  # 第X章
        section_pattern = re.compile(r'^\s*(第[零一二三四五六七八九十百千]+节[\s\u3000]+.*)$')  # 第X节
        special_pattern = re.compile(r'^\s*(附[\s\u3000]*则|总[\s\u3000]*则|分[\s\u3000]*则)$')  # 附则、总则、分则
        
        current_part = ""    # 当前编
        current_chapter = "" # 当前章
        current_section = "" # 当前节
        
        def get_full_chapter():
            """构建完整的章节路径"""
            parts = []
            if current_part:
                parts.append(current_part)
            if current_chapter:
                parts.append(current_chapter)
            if current_section:
                parts.append(current_section)
            return " / ".join(parts) if parts else ""
        
        def is_structure_line(line_strip):
            """检查是否是结构行（编/章/节/特殊章节）"""
            return (part_pattern.match(line_strip) or 
                    chapter_pattern.match(line_strip) or 
                    section_pattern.match(line_strip) or 
                    special_pattern.match(line_strip))
        
        def update_structure(line_strip):
            """更新当前结构层级"""
            nonlocal current_part, current_chapter, current_section
            
            if part_pattern.match(line_strip):
                current_part = line_strip
                current_chapter = ""  # 进入新编时清空章
                current_section = ""  # 清空节
            elif chapter_pattern.match(line_strip):
                current_chapter = line_strip
                current_section = ""  # 进入新章时清空节
            elif section_pattern.match(line_strip):
                current_section = line_strip
            elif special_pattern.match(line_strip):
                # 附则等特殊章节，作为独立的"编"处理
                current_part = line_strip
                current_chapter = ""
                current_section = ""
        
        # 初始层级：扫描第一条之前的内容
        pre_text = full_text[:matches[0].start()]
        for line in pre_text.split('\n'):
            line_strip = line.strip()
            if is_structure_line(line_strip):
                update_structure(line_strip)

        for i, match in enumerate(matches):
            start = match.start()
            article_display = match.group(2).strip()
            # 使用顺序编号，避免"第X条之一"等特殊条号冲突
            article_num = i + 1
            
            # 确定结束位置
            end = matches[i+1].start() if i+1 < len(matches) else len(full_text)
            
            # 提取原始内容块
            raw_content = full_text[start:end]
            lines = raw_content.split('\n')
            
            cleaned_lines = []
            found_next_structures = []  # 记录发现的结构行
            
            for line in lines:
                line_strip = line.strip()
                if not line_strip:
                    cleaned_lines.append(line)
                    continue
                    
                # 检查是否是结构行
                if is_structure_line(line_strip):
                    found_next_structures.append(line_strip)
                    continue  # 不包含在当前条文中
                
                cleaned_lines.append(line)
            
            # 记录当前条文的章节（使用更新前的层级）
            chapter_for_article = get_full_chapter()
            
            # 重新组合内容
            content_str = '\n'.join(cleaned_lines).strip()
            
            articles.append({
                "article_num": article_num,
                "article_display": article_display,
                "content": content_str,
                "chapter": chapter_for_article,
                "section": ""  # section 已合并到 chapter 路径中
            })
            
            # 更新结构层级，供下一条使用
            for struct_line in found_next_structures:
                update_structure(struct_line)

        return articles

    def chinese_to_number(self, chn):
        """中文数字转阿拉伯数字 (修复版)"""
        try:
            if chn.isdigit(): return int(chn)
            
            chinese_map = {'零':0, '一':1, '二':2, '三':3, '四':4, '五':5, '六':6, '七':7, '八':8, '九':9, '十':10, '百':100, '千':1000}
            
            # 特殊情况处理：十、十一...十九 -> 一十、一十一...一十九
            if chn.startswith('十'):
                chn = '一' + chn
                
            result = 0
            unit_val = 0 # 当前累积的小节值
            
            for char in chn:
                if char not in chinese_map:
                    continue
                val = chinese_map[char]
                
                if val >= 10: # 是单位
                    if unit_val == 0: unit_val = 1 # 处理 "十" 这种前面没数字的情况，但上面已经补了"一"，这里是双保险
                    result += unit_val * val
                    unit_val = 0 # 归零，准备接个位数
                else: # 是数字
                    unit_val = val
                    
            result += unit_val # 加上最后的个位数
            return result
        except:
            return 0

    def generate_id(self, title):
        return hashlib.md5(title.encode('utf-8')).hexdigest()[:16]

    def read_docx(self, file_path):
        """读取 Word 文档并提取文本"""
        try:
            doc = Document(file_path)
            paragraphs = []
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    paragraphs.append(text)
            content = '\n'.join(paragraphs)
            logging.info(f"   📄 Word 文档读取成功，共 {len(paragraphs)} 段")
            return content
        except Exception as e:
            logging.error(f"❌ 读取 Word 文档失败: {e}")
            return None

    def run(self):
        if not os.path.exists(self.input_dir):
            os.makedirs(self.input_dir)
            logging.info(f"📁 已创建目录 {self.input_dir}，请将 txt/md 文件放入其中。")
            return

        # 支持 txt, md, docx 格式
        supported_ext = ['.txt', '.md']
        if DOCX_SUPPORTED:
            supported_ext.append('.docx')
        
        files = [f for f in os.listdir(self.input_dir) if os.path.splitext(f)[1].lower() in supported_ext]
        if not files:
            logging.warning(f"⚠️ {self.input_dir} 目录为空，请放入法规文件（支持: {', '.join(supported_ext)}）！")
            return

        logging.info(f"🚀 发现 {len(files)} 个文件，开始处理...")
        
        for file in files:
            file_path = os.path.join(self.input_dir, file)
            title = os.path.splitext(file)[0]  # 文件名作为标题
             # 去除文件名中的 (2024) 等修饰以保持干净，或者保留
            
            logging.info(f"📄 处理: {title}")
            
            # 根据文件类型读取内容
            ext = os.path.splitext(file)[1].lower()
            
            if ext == '.docx':
                content = self.read_docx(file_path)
                if content is None:
                    continue
            else:
                # txt 或 md 文件
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    try:
                        with open(file_path, 'r', encoding='gbk') as f:
                            content = f.read()
                    except:
                        logging.error(f"❌ 无法读取文件 {file} (编码错误)")
                        continue

            # 1. 解析元数据
            metadata = self.parse_metadata(content)
            
            # 优先使用从文档末尾解析到的标题
            if metadata.get("title_from_tail"):
                title = metadata["title_from_tail"]
                logging.info(f"   📋 使用文档中的标题: {title}")
            
            law_id = self.generate_id(title)
            
            # 检查是否已存在该法规，保留已有的有效数据
            existing_law = self.db.laws.find_one({"law_id": law_id})
            
            # 智能合并：如果新解析的是默认值，但数据库中有更好的值，则保留数据库的值
            final_issue_org = metadata["issue_org"]
            final_issue_date = metadata["issue_date"] or "2000-01-01"
            final_effect_date = metadata["effect_date"] or "2000-01-01"
            
            if existing_law:
                # 如果新值是默认值，但旧值更有意义，则保留旧值
                if final_issue_date == "2000-01-01" and existing_law.get("issue_date") and existing_law["issue_date"] != "2000-01-01":
                    final_issue_date = existing_law["issue_date"]
                    logging.info(f"   📅 保留已有的发布日期: {final_issue_date}")
                    
                if final_effect_date == "2000-01-01" and existing_law.get("effect_date") and existing_law["effect_date"] != "2000-01-01":
                    final_effect_date = existing_law["effect_date"]
                    logging.info(f"   📅 保留已有的实施日期: {final_effect_date}")
                
                # 如果新的发布机关是通用默认值，但旧值更具体，则保留旧值
                generic_orgs = ["公安部", "全国人民代表大会及其常务委员会"]
                if final_issue_org in generic_orgs and existing_law.get("issue_org") and existing_law["issue_org"] not in generic_orgs:
                    final_issue_org = existing_law["issue_org"]
                    logging.info(f"   🏛️ 保留已有的发布机关: {final_issue_org}")
            
            law_doc = {
                "law_id": law_id,
                "title": title,
                "status": metadata["status"],
                "issue_org": final_issue_org,
                "issue_date": final_issue_date,
                "effect_date": final_effect_date,
                "category": metadata["category"],
                "level": metadata["level"],
                "content_type": "text",
                "summary": metadata.get("summary", "")
            }
            
            # 2. 插入法规主表
            try:
                self.db.laws.replace_one({"law_id": law_id}, law_doc, upsert=True)
            except Exception as e:
                logging.error(f"入库法规失败: {e}")
                continue

            # 3. 拆分条文
            articles = self.split_articles(content)
            
            # 4. 插入条文表 (先删后插)
            self.db.law_articles.delete_many({"law_id": law_id})
            
            article_docs = []
            for art in articles:
                art["law_id"] = law_id
                article_docs.append(art)
            
            if article_docs:
                try:
                    # ordered=False 允许跳过重复项继续插入
                    self.db.law_articles.insert_many(article_docs, ordered=False)
                except Exception as e:
                    # BulkWriteError 可能因重复键引发，但部分数据已成功插入
                    logging.warning(f"   ⚠️ 部分条文插入时遇到问题: {str(e)[:100]}")
                
                inserted_count = self.db.law_articles.count_documents({"law_id": law_id})
                logging.info(f"   ✅ 成功导入 {inserted_count} 条条文")
            else:
                logging.warning(f"   ⚠️ 未提取到条文，请检查格式")

        logging.info("🎉 所有文件处理完成！")

if __name__ == "__main__":
    importer = LocalImporter()
    importer.run()
