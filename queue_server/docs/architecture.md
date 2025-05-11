# 아키텍처 설계

## 설계 목적

- 트래픽 집중 상황에서도 안정적인 서비스를 제공하기 위해, 대기열 서버를 포함한 전체 시스템의 **네트워크 흐름 및 계층별 역할**을 정의한다.
- 주요 목표:
  - 트래픽 분산
  - 요청 속도 제어
  - 대기열 흐름 제어
  - API 서버 보호


## 클라이언트 → 퍼블릭 네트워크

- 사용자 단말기(브라우저, 앱 등)에서 대기열 서버의 도메인(queue.com)으로 요청 발생
- 해당 DNS rocord에는 a record로 두개의 L7 LB의 IPv4 저장

### 고려 사항
 
- 하나의 LB가 다운되었을 경우를 고려해 다른 AZ에 최소한 두개 이상을 LB를 둔다 (추가적으로 트래픽 분산으로 이점도 가짐)
- DNS 기반 Load Balancing의 경우 LB의 health check가 불가능하기에 record update 전파가 필요함
- Anycast + BGP 기반 구성


## L7 프록시 / 게이트웨이 계층

- 예: **Nginx, Envoy, API Gateway**
- 요청을 대기열 서버(FastAPI)로 전달하며, 아래 역할 수행

### 주요 역할

- TLS 인증은 해당 LB에서 처리하고 뒷단은 http로 처리 (TLS termination)
- 이중화된 대기열 서버로 Load balancing을 진행 + health check
- 요청 속도 제한 (Rate Limiting)

### 고려 사항

- LB가 이중화 되어있다면, TLS 인증서는 어떻게 배치하고, 갱신할 것인가?
- LB 알고리즘은 어떤것을 고를 것인가?
  - client와 affinity를 고려할까? → sticky session이 필요한가? polling 기반 요청 구조라면 affinity는 필수가 아닐 수도 있음.
    - 대신 클라이언트가 요청마다 ticket ID를 보내고, 상태는 Redis가 공유하므로 stateless 설계 유지 가능
- client의 connection이 많이 몰릴 텐데, connection pool size, worker의 event handling(비동기, multi-thread, pre-fork)


## 대기열 서버 (FastAPI)

- 대기열 핵심 로직이 구현된 백엔드
- 다음 역할을 수행:
  - 처리량 판단
  - ticket 발급 및 TTL 저장
  - 대기열 정렬
  - polling 응답 처리
  - check-in 처리 및 통과 권한 발급

### 구성

- Uvicorn + FastAPI + Gunicorn (multi-worker)

### 고려 사항

- gunicorn multi-worker vs uvicorn container
- 대기열 서버 auto-scailing을 어떤 metric으로 할까?

## 저장소 및 캐시 계층

- 요청 처리에 필요한 데이터를 저장하고 관리

### Redis

대기열 서버들 간의 티겟 consistency 보장 및 빠른 접근이 가능한 in-memory 저장소

- 대기열 저장 (`ZADD`, `ZREM`, `ZCARD`)
- ticket 관리 (UUID → TTL)
- request 카운터 (`INCR`, `EXPIRE`)

#### 고려사항

- 여러 대기열 서버에서, redis에 접근하면 동시성 문제는 어떻게 해결할까?
  - redis Lock
- 티켓의 만료기간을 어떻게 잡을까?
- 사용자의 대기열 이탈의 경우, queue 상태 관리는 어떻게 할까?

### MongoDB (또는 Influx, ClickHouse)

- 처리 로그 저장
- 사용자 히스토리
- 시간 기반 집계

#### 고려사항

- 로그 데이터의 특성상 read보다 write가 많기에 이에 맞는 LSM tree 기반 DB 선정
- 단위 시간마다 집계가 필요하기에 sliding window 기반 자료구조를 따로 두는 것도 고려 가능

## API 서버 (비즈니스 로직 서버)

- 실제 서비스 로직 (주문, 결제 등)을 처리
- 오직 ticket이 유효하거나 처리량 여유가 있을 경우에만 진입 가능
