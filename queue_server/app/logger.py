from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

mongo_client = AsyncIOMotorClient("mongodb://mongodb:27017")
db = mongo_client["ticketing"]
log_collection = db["processed_log"]


# 처리량 집계 함수
async def get_recent_count():
    now = datetime.now()
    minute_ago = now - timedelta(minutes=1)
    count = await log_collection.count_documents({"timestamp": {"$gte": minute_ago}})
    return count


# 처리 로그 기록
async def log_user_entry(user_id: str):
    await log_collection.insert_one({"user_id": user_id, "timestamp": datetime.now()})
