import asyncio
import httpx

BASE_URL = "http://localhost:8000"
CLIENT_COUNT = 10000
CHECK_RETRY = 10
CHECK_INTERVAL = 1


async def simulate_user(user_no: int, start_event: asyncio.Event):
    await start_event.wait()  # 출발 신호 기다리기
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(f"{BASE_URL}/enter")  # <-- get → post 수정
            data = res.json()
            user_id = data["id"]
            print(f"[User {user_no}] ENTER: {data['message']}")

            if data.get("enter_passed"):
                return

            for i in range(CHECK_RETRY):
                res = await client.post(f"{BASE_URL}/check-in/{user_id}")
                result = res.json()
                print(f"[User {user_no}] CHECK-IN {i+1}: {result['message']}")
                if result.get("message") in ["입장 허가됨", "입장권이 발급되었습니다"]:
                    return
                await asyncio.sleep(CHECK_INTERVAL)

            print(f"[User {user_no}] ⌛ 종료: 최대 시도 횟수 초과")

        except Exception as e:
            print(f"[User {user_no}] ❌ 오류 발생: {e}")


async def main():
    start_event = asyncio.Event()
    tasks = [simulate_user(i, start_event) for i in range(1, CLIENT_COUNT + 1)]
    print(f"🚦 모든 유저 준비 완료, 1초 후 출발합니다.")
    await asyncio.sleep(1)
    start_event.set()  # 동시에 모두 출발
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
