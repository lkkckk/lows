import asyncio
import os
import sys
from spiders.law_star_spider import LawStarSpider
import subprocess

# 将当前目录添加到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def run_crawling_batch():
    # 修正后的法律列表
    law_titles = [
        "中华人民共和国治安管理处罚法", # 2026版本在 Law-Star 通常标为 2025修订
        "中华人民共和国刑法",
        "中华人民共和国刑事诉讼法",
        "公安机关办理行政案件程序规定",
        "公安机关办理刑事案件程序规定",
        "中华人民共和国反电信网络诈骗法",
        "中华人民共和国网络安全法",
        "中华人民共和国道路交通安全法",
        "中华人民共和国出境入境管理法",
        "中华人民共和国公民出境入境管理法",
        "中华人民共和国禁毒法",
        "中华人民共和国反恐怖主义法"
    ]

    spider = LawStarSpider()
    
    print(f"🚀 开始批量抓取 {len(law_titles)} 部法规...")
    
    for title in law_titles:
        try:
            print(f"--- 正在处理: {title} ---")
            await spider.search_and_parse(title)
            # 适当延时，模拟真人操作
            await asyncio.sleep(3)
        except Exception as e:
            print(f"❌ 处理 {title} 失败: {str(e)}")

    print("\n✅ 抓取阶段完成！")

def run_import():
    print("📥 开始导入数据到 MongoDB...")
    try:
        # 调用已有的导入脚本
        result = subprocess.run(["python", "import_data.py"], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"⚠️ 导入警告/错误: {result.stderr}")
        print("✅ 导入阶段完成！")
    except Exception as e:
        print(f"❌ 导入失败: {str(e)}")

if __name__ == "__main__":
    # 1. 运行异步抓取
    asyncio.run(run_crawling_batch())
    
    # 2. 运行同步导入
    run_import()
    
    print("\n🎉 全流程执行完毕！请刷新前端页面查看更新。")
