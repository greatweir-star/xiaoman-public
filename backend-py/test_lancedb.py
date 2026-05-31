"""LanceDB 对接测试"""

import lancedb
import numpy as np
import pyarrow as pa
import shutil
import os

DB_PATH = "./test_lancedb"

# 清理旧数据
if os.path.exists(DB_PATH):
    shutil.rmtree(DB_PATH)

# 1. 连接 LanceDB
db = lancedb.connect(DB_PATH)
print("1. LanceDB 连接成功")

# 2. 创建表
schema = pa.schema([
    ("id", pa.string()),
    ("text", pa.string()),
    ("vector", pa.list_(pa.float32(), 3072)),
])

table = db.create_table("test_memories", schema=schema, mode="overwrite")
print("2. 表创建成功")

# 3. 插入数据（模拟小满的记忆）
table.add([
    {
        "id": "mem-1",
        "text": "用户叫阿梨，初三女生",
        "vector": np.random.rand(3072).astype(np.float32).tolist(),
    },
    {
        "id": "mem-2",
        "text": "用户数学成绩最好，物理最差",
        "vector": np.random.rand(3072).astype(np.float32).tolist(),
    },
    {
        "id": "mem-3",
        "text": "用户喜欢吃火锅，不喜欢吃香菜",
        "vector": np.random.rand(3072).astype(np.float32).tolist(),
    },
])
print("3. 插入 3 条记忆成功")

# 4. 向量搜索
query_vector = np.random.rand(3072).astype(np.float32).tolist()
results = table.search(query_vector).limit(2).to_list()
print(f"4. 向量搜索成功，返回 {len(results)} 条结果")
for r in results:
    print(f"   - {r['text'][:30]}... (距离: {r.get('_distance', 'N/A')})")

# 5. 清理
shutil.rmtree(DB_PATH)
print("5. 测试完成，LanceDB 工作正常 ✓")
