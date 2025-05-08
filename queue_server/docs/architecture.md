# 아키텍처 설계

## 설계 목적

- 트래픽 집중 상황에서도 안정적인 서비스를 제공하기 위해, 대기열 서버를 포함한 전체 시스템의 **네트워크 흐름 및 계층별 역할**을 정의한다.
- 주요 목표:
  - 트래픽 분산
  - 인증 및 보안 강화
  - 요청 속도 제어
  - 대기열 흐름 제어
  - API 서버 보호

---

## 1단계: 클라이언트 → 퍼블릭 네트워크

- 사용자 단말기(브라우저, 앱 등)에서 대기열 서버의 도메인으로 요청 발생
- HTTPS 기반 통신을 사용하며, **CDN 또는 Cloud Load Balancer를 통해 우선 라우팅**

### 고려 사항
 
- DDoS 방지 (Cloudflare, AWS Shield 등)
- TLS termination
- 정적 자산 캐싱

---

## 2단계: L7 프록시 / 게이트웨이 계층

- 예: **Nginx, Envoy, API Gateway**
- 요청을 대기열 서버(FastAPI)로 전달하며, 아래 역할 수행

### 주요 역할

- 요청 속도 제한 (Rate Limiting)
- 헤더 검사 및 인증 토큰 유효성 확인
- 라우팅 제어 (`/enter`, `/check-in`, `/position` 등)
- **건강 검사** (대기열 서버 상태 확인)
- 요청 로그 기록

---

## 3단계: 대기열 서버 (FastAPI)

- 대기열 핵심 로직이 구현된 백엔드
- 다음 역할을 수행:
  - 처리량 판단
  - ticket 발급 및 TTL 저장
  - 대기열 정렬
  - polling 응답 처리
  - check-in 처리 및 통과 권한 발급

### 구성

- Uvicorn + FastAPI + Gunicorn (multi-worker)
- 환경에 따라 Redis/Mongo 연결

---

## 4단계: 저장소 및 캐시 계층

- 요청 처리에 필요한 데이터를 저장하고 관리

### Redis

- 대기열 저장 (`ZADD`, `ZREM`, `ZCARD`)
- ticket 관리 (UUID → TTL)
- request 카운터 (`INCR`, `EXPIRE`)

### MongoDB (또는 Influx, ClickHouse)

- 처리 로그 저장
- 사용자 히스토리
- 시간 기반 집계

---

## 5단계: API 서버 (비즈니스 로직 서버)

- FastAPI 또는 기타 백엔드 서버
- 실제 서비스 로직 (주문, 결제 등)을 처리
- 오직 ticket이 유효하거나 처리량 여유가 있을 경우에만 진입 가능

---

## 🗂️ 트래픽 흐름 요약

```plaintext
Client
  ↓
CDN / Cloud Load Balancer
  ↓
API Gateway (Nginx / Envoy)
  ↓
[대기열 서버 FastAPI]
  ↙            ↘
Redis         MongoDB
  ↓
[Main API Server]
```