# 서비스 아키텍처 설계

## 필요 컴포넌트 정의

### Object Storage 

- 이미지, 동영상을 저장하기 위한 스토리지
- block storage보다 비용 저렴
- API 형태로 read, write이 가능
- object에 접근하기 위한 endpoint 생성 가능

#### 고려사항

- client는 조회만 가능하고, write는 API 서버에서만 처리
- 특정 사용자들에게만 제공할 수 있는 policy가 있어야함

### CDN

- 빠른 정적파일 (이미지, 동영상)을 제공하기 위한 서비스
- Obect Storage의 정적파일을 캐싱
- HTTP 2.0, 3.0 의 기능을 최대한 활용해서 빠른 데이터 전송

#### 고려사항

- 기존 파일을 수정한 경우 client의 캐시 expired가 될 때까지 반영이 안됌
    - 기존 파일 업데이트 시, 새로운 파일 생성하여 캐시 invalidate 설정
    - cache 기간을 짧게 두기
- 너무 큰 컨텐츠 파일에 대한 전송 비용 고려


### L7 LB (gateway)

- TLS termination -> tls handshake 과정을 LB가 대신함
- API 서버로 로드밸런싱 진행
    - login session affinity를 위한 source IP hashing 기반 load balancing
- API 서버 health & latency check


### API server

- 업로드, 메타데이터 처리, 인증, 피드 제공 등 비즈니스 로직 처리

#### 고려사항

- JWT 또는 OAuth2 기반 인증 처리
- RESTful API 설계, 버전 관리 필요 (/v1/)
- 수평 확장 구조 (stateless + autoscaling)
- abuse/rate limit 제어 로직 필요

### In-memory cache store (Redis)

- 실시간 피드, 인기 콘텐츠, 세션 정보 캐싱
- TTL 기반 캐시 전략 적용

#### 고려사항

- Hot key 방지 (샤딩, LRU 정책 등)
- 캐시 miss 시 백엔드 fallback 처리 필요
- 실시간 통계 또는 순위 계산시 Sorted Set 활용


### DB

- 콘텐츠 메타데이터, 사용자 정보, 댓글 등 영속 저장소

#### 고려사항

- RDB (PostgreSQL) 또는 Document DB (MongoDB) 혼합 사용 고려
- 파티셔닝/샤딩을 통한 대용량 트래픽 분산
- 인덱싱 최적화 (검색, 정렬)
- 백업 및 장애 복구 정책 필수

### Transcoding Server

- 동영상 트랜스코딩, 이미지 썸네일 생성, 해상도 변환 등 처리 담당

#### 고려사항

- 비동기 작업 큐 연동 (e.g., Kafka, RabbitMQ)
- HLS/DASH 세그먼트 생성 및 metadata 업데이트
- GPU 리소스 사용 여부에 따라 별도 워커 노드 구성
- 실패/지연/재시도 로직 포함

### Search Engine (Elastic Search)

- 게시글, 해시태그, 댓글 검색 기능 제공

#### 고려사항
- full-text 검색을 위한 인덱스 구성
- 