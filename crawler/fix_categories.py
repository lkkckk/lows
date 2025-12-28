from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017')
db = client['law_system']

# 清理分类名称
targets = ['程序法律', '程序法规']
new_name = '程序规定'

laws_count = db.laws.update_many(
    {'category': {'$in': targets}},
    {'$set': {'category': new_name}}
).modified_count

articles_count = db.law_articles.update_many(
    {'category': {'$in': targets}},
    {'$set': {'category': new_name}}
).modified_count

print(f"修正了 {laws_count} 部法规和 {articles_count} 条条文的分类名称。")

# 检查当前所有分类
current_categories = db.laws.distinct('category')
print(f"当前数据库中的全部分类: {current_categories}")
