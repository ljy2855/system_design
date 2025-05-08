# 네트워크 계층 설계 - 이슈 대응 중심 설계

## 설계 목적

- 대기열 서버 아키텍처를 **현실적인 네트워크 환경에서 발생 가능한 장애**에 대응할 수 있도록 설계한다.
- 단순 라우팅/트래픽 처리뿐 아니라, **지연, 장애, 보안, 부하 분산** 등 다양한 이슈에 대응할 수 있도록 설계

---

## 1. 트래픽 폭주 (Burst Traffic)

### 문제
- 이벤트 시작 시 **짧은 시간에 수만 건의 요청**이 집중 발생
- L7 프록시 또는 FastAPI 서버가 처리 불가능한 수준까지 올라감

### 대응 설계
- **CDN 및 Cloud Load Balancer**를 가장 앞단에 배치해 초당 요청 수 완화
- **L7 Proxy (Nginx/Envoy)**에서 rate-limit 적용 (ex: IP당 20 req/sec)
- **FastAPI 대기열 서버는 Redis의 INCR로 초당 요청 수 추적** 후, 일정 이상은 429 응답 또는 ticket 발급 유도

---

## 🐢 2. 네트워크 지연 (Latency)

### 문제
- 지역 간 요청 편차, ISP 경로 지연 등으로 인해 RTT 증가
- 예상 대기 시간과 실제 경험 사이의 괴리 발생

### 대응 설계
- **지역 기반 CDN 구성** (예: Cloudflare, AWS CloudFront)
- **대기열 예상 시간(ETA)을 지역/지연에 따라 보정**
- Redis의 응답 시간 측정하여 평균 지연 값을 ETA 추정에 반영

---

## 💥 3. L7 프록시 장애 (Nginx, Envoy)

### 문제
- 프록시 서버의 설정 오류, 과도한 부하, 재시작 시 요청 손실

### 대응 설계
- **Nginx는 reload 없이 설정 변경 가능하도록 설계**
- **Active-Standby 구성 + 헬스체크 기반 로드 밸런싱**
- 모든 프록시 노드는 **readiness check + autoscaling target**

---

## 📉 4. 연결 상태 불안정 (Client Drop, 중간 끊김)

### 문제
- 클라이언트의 중간 이탈 시 대기열 자원 낭비
- 사용자 체감 대기시간에 비해 실제 입장이 늦어짐

### 대응 설계
- 클라이언트는 `polling` 또는 `WebSocket` 기반 **heartbeat 신호 주기적 전송**
- Redis ZSET의 `last_seen_timestamp` 기준으로 일정 시간 미응답 시 자동 제거
- TTL 적용 (예: 3분) → ticket 및 queue entry 만료

---

## 🔐 5. 악의적 요청 / 공격

### 문제
- 티켓 무작위 생성 시도, 요청 flooding, queue bypass 공격

### 대응 설계
- 티켓은 **UUID + Redis에만 유효성 저장 (중앙 인증)**
- 중요 요청에 **JWT 기반 서명** 적용해 변조 방지
- IP + User-Agent 기반 **rate limit** / **blacklist 제어**
- 클라이언트에서 `ticket_id + nonce` 조합으로 check-in 요청

---

## 🧨 6. DNS/SSL 문제

### 문제
- CDN, 로드밸런서가 도메인 또는 인증서 오류로 요청 실패

### 대응 설계
- **도메인 헬스체크 및 다중 Origin 설정** (Failover)
- 인증서 자동 갱신 (Let's Encrypt + Certbot / AWS ACM 사용)
- 내부 서비스는 mTLS + 서비스 Mesh (예: Istio) 고려 가능

---

## 🛡️ 7. 비정상 라우팅 또는 리다이렉션 오류

### 문제
- 티켓 없이 API 서버에 직접 진입하거나 경로 우회

### 대응 설계
- 모든 API 서버 요청은 **Gateway를 통해서만 접근 가능하도록 네트워크 격리**
- 내부 서비스 간 통신에 **Internal ALB or Service Mesh 규칙** 적용
- FastAPI에서 ticket 검증 실패 시 즉시 403 응답

---

## ✅ 통합 대응 아키텍처 요약

```plaintext
[Client]
   ↓
[CDN / Cloud LB]
   ↓
[API Gateway (Nginx/Envoy)]
   ↓
[Queue Server (FastAPI)]
   ↙︎           ↘︎
[Redis]     [MongoDB]
   ↓
[Main API Server]
