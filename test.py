from pymongo import MongoClient

# 改成您实际的 MongoDB 连接地址（一般默认本机 27017）
client = MongoClient("mongodb://localhost:27017/")

# 列出所有数据库
for db_name in client.list_database_names():
    print(f"数据库: {db_name}")
    db = client[db_name]
    # 列出每个数据库中的集合
    for coll_name in db.list_collection_names():
        count = db[coll_name].count_documents({})
        if count > 0:
            print(f"  └─ 集合: {coll_name}, 文档数: {count}")