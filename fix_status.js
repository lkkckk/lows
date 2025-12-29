// 批量将所有"有效"状态更新为"现行有效"
db = db.getSiblingDB('law_system');

// 查看当前有多少条状态为"有效"的记录
var count = db.laws.countDocuments({ status: '有效' });
print('需要修复的记录数: ' + count);

// 执行批量更新
var result = db.laws.updateMany(
    { status: '有效' },
    { $set: { status: '现行有效' } }
);

print('已修改: ' + result.modifiedCount + ' 条记录');
