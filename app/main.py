import uuid
from fastapi import FastAPI, HTTPException
import redis

from app.logger import get_recent_count, log_user_entry

app = FastAPI()

r = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)

QUEUE_KEY = "ticket_queue"
PROCESSED_COUNT_KEY = "processed_count"
WAIT_THRESHOLD = 100  # 대기열 최대 길이
TICKET_TTL = 60  # 대기열 만료시간 60초
DAILY_CAPACITY = 100  # 일일 처리 한도


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/enter")
async def enter_queue():
    processed_count = await get_recent_count()
    user_id = str(uuid.uuid4())
    await log_user_entry(user_id)

    if processed_count < DAILY_CAPACITY:
        return {"message": "즉시 입장 허가됨", "id": user_id, "enter_passed": True}

    # 대기열 등록
    r.rpush(QUEUE_KEY, user_id)
    return {"message": "대기열에 등록되었습니다", "id": user_id, "enter_passed": False}


@app.get("/position/{user_id}")
def get_position(user_id: str):
    queue = r.lrange(QUEUE_KEY, 0, -1)
    if user_id not in queue:
        raise HTTPException(status_code=404, detail="대기열에 없음")
    position = queue.index(user_id) + 1
    return {"position": position}


@app.post("/check-in/{user_id}")
async def check_in(user_id: str):
    queue = r.lrange(QUEUE_KEY, 0, -1)

    if user_id not in queue:
        if r.exists(f"ticket_issued:{user_id}"):
            return {"message": "입장권이 발급되었습니다", "ticket": True}
        raise HTTPException(status_code=404, detail="대기열에 없음")

    processed_count = await get_recent_count()
    if processed_count >= DAILY_CAPACITY:
        r.lrem(QUEUE_KEY, 0, user_id)
        r.setex(f"ticket_issued:{user_id}", TICKET_TTL, "true")
        return {"message": "입장권이 발급되었습니다", "ticket": True}

    if queue[0] == user_id:
        r.lpop(QUEUE_KEY)
        await log_user_entry(user_id)
        return {"message": "입장 허가됨", "ticket": False}

    return {"message": "아직 순서 아님", "position": queue.index(user_id) + 1}
