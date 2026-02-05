import re
from typing import Optional, Tuple

# Mocking the UPDATED helper functions from law_service.py

def _extract_law_keyword(query: str) -> str:
    cn_nums = "\u96f6\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e9d\u5341\u767e\u5343"
    text = re.sub(rf"\u7b2c?[{cn_nums}]+\u6761([之][{cn_nums}]+)?", " ", query)
    text = re.sub(r"\u7b2c?\d+\u6761", " ", text)
    text = re.sub(r"^(请问|问下|问一下|咨询|请教)", "", text)
    text = re.sub(r"(是什么内容|是什么|是啥|内容|规定|条文|规定内容|的内容|具体内容|主要内容|含义|指什么|什么意思|指啥)$", "", text)
    text = re.sub(r"[\s\?\uff1f\u3002\uff0c\uff1b\uff1a\u2026]+$", "", text)
    text = re.sub(r"[《》<>〈〉（）()\[\]【】]", "", text)
    return text.strip()

def _chinese_to_arabic(chinese_num: str) -> int:
    chinese_num_map = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000
    }
    if not chinese_num:
        return 0
    result = 0
    current = 0
    for char in chinese_num:
        num = chinese_num_map.get(char, 0)
        if num >= 10:
            if current == 0:
                current = 1
            result += current * num
            current = 0
        else:
            current = num
    return result + current

def parse_article_input(input_str: str) -> Tuple[Optional[int], Optional[str]]:
    chinese_num_map = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000
    }

    pattern1 = r'第([零一二三四五六七八九十百千]+)条([之][零一二三四五六七八九十]+)?'
    match = re.search(pattern1, input_str)
    if match:
        chinese_num = match.group(1)
        sub_index = match.group(2)
        return (_chinese_to_arabic(chinese_num), sub_index)

    pattern2 = r'(\d+)条'
    match = re.search(pattern2, input_str)
    if match:
        return (int(match.group(1)), None)

    pattern3 = r'^\d+$'
    if re.match(pattern3, input_str.strip()):
        return (int(input_str.strip()), None)

    return (None, None)

def test_cases():
    cases = [
        "《刑法》第十八条",
        "刑法第十八条",
        "中华人民共和国刑法第18条",
        "第18条",
        "刑法第十七条之一",
        "刑法第17.1条",  
        "《刑法》",
        "治安管理处罚法第二十条之二"
    ]
    
    print("--- Testing UPDATED Parsing Logic ---")
    for case in cases:
        article_num, sub_index = parse_article_input(case)
        law_keyword = _extract_law_keyword(case)
        
        print(f"Input: '{case}'")
        print(f"  -> ArticleNum: {article_num}")
        print(f"  -> SubIndex:   {sub_index}")
        print(f"  -> LawKeyword: '{law_keyword}' (should be clean of brackets)")
        print("-" * 30)

if __name__ == "__main__":
    test_cases()
