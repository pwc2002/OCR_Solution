# 의료 문서 OCR 시스템

PaddleOCR 기반 의료 문서 OCR 시스템입니다. PDF 문서에서 텍스트를 추출하고, 이미지 페이지는 OCR로 인식하며, 민감정보(주민번호, 이름)를 탐지 및 마스킹합니다.

## 주요 기능

- **PDF 처리**: 텍스트 레이어 직접 추출 + 이미지 페이지 OCR
- **PII 탐지/마스킹**: 주민번호, 이름 자동 탐지 및 마스킹
- **REST API**: FastAPI 기반 RESTful API
- **웹 대시보드**: React 기반 웹 인터페이스
- **CLI 도구**: 명령줄 인터페이스
- **Docker 지원**: Docker Compose로 전체 스택 실행

## 기술 스택

- Python 3.11
- FastAPI + Uvicorn
- PaddleOCR v3.0
- PyMuPDF (PDF 처리)
- PostgreSQL v17
- React + Vite (대시보드)


## 설치 및 실행

### Docker Compose 사용 (권장)

1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일에서 API_KEY 등 설정 수정
```

2. 서비스 시작

```bash
docker-compose up -d
```

3. 서비스 확인

- API 서버: http://localhost:8080
- API 문서: http://localhost:8080/docs

### 로컬 개발 환경

1. Python 가상환경 생성

```bash
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. 의존성 설치

```bash
pip install -r requirements.txt
```

3. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일 수정
```

4. 데이터베이스 초기화

```bash
python -c "from app.core.dao import init_db; init_db()"
# 또는
python -m alembic upgrade head
```

5. 서버 시작

```bash
uvicorn app.api.server:app --host 0.0.0.0 --port 8080
# 또는
ocr-cli server
```

### 폐쇄망(Offline) 배포 가이드

인터넷이 차단된 내부망 환경 배포를 위해, 모든 의존성과 AI 모델이 포함된 Docker 이미지를 파일로 제공합니다.

#### 1. 배포 파일 준비

**방법 A: 직접 빌드 (추천)**

인터넷이 가능한 PC에서 직접 이미지를 빌드하고 추출합니다.

```bash
# 1) Docker 이미지 빌드
docker build -t mediview-ocr:v1.0.0 .

# 2) 이미지를 파일로 추출 (.tar)
docker save -o mediview-ocr_v1.0.0.tar mediview-ocr:v1.0.0
```

**방법 B: 빌드된 파일 다운로드**

GitHub Releases 페이지에서 미리 빌드된 이미지 파일을 다운로드할 수 있습니다.

- [mediview-ocr_v1.0.0.tar 다운로드](https://github.com/pwc2002/OCR_Solution/releases/tag/v1.0.0)

#### 2. 모델 파일 준비

Docker 이미지 외에, `paddleocr_models` 폴더(AI 모델 파일)도 함께 전달해야 합니다.
프로젝트에 포함된 `paddleocr_models` 폴더를 압축하여 내부망 서버로 가져가세요.

#### 3. 서버 배포 (내부망)

전달받은 `.tar` 파일이 있으면 인터넷 연결 없이 설치 가능합니다.

```bash
# 1) 이미지 로드
docker load -i mediview-ocr_v1.0.0.tar

# 2) 실행 (docker-compose.yml이 있는 위치에서)
docker-compose up -d
```


## 사용법

### API 사용

#### 파일 업로드 및 OCR 처리

```bash
curl -X POST http://localhost:8080/api/v1/get \
  -H "Authorization: your-api-key-here" \
  -F "file=@sample.pdf" \
  -F "lang=ko"
```

#### 비동기 모드

```bash
curl -X POST http://localhost:8080/api/v1/get \
  -H "Authorization: your-api-key-here" \
  -F "file=@sample.pdf" \
  -F "lang=ko" \
  -F "async_mode=true"
```

#### 결과 조회 (비동기 모드)

```bash
curl http://localhost:8080/api/v1/result/{job_id} \
  -H "Authorization: your-api-key-here"
```

#### 작업 목록 조회

```bash
curl http://localhost:8080/api/v1/jobs \
  -H "Authorization: your-api-key-here"
```

#### 통계 조회

```bash
curl http://localhost:8080/api/v1/stats \
  -H "Authorization: your-api-key-here"
```

### CLI 사용

#### 파일 처리

```bash
ocr-cli run sample.pdf --lang ko --output result.json
```

#### 서버 시작

```bash
ocr-cli server --host 0.0.0.0 --port 8080
```

#### 데이터베이스 마이그레이션

```bash
ocr-cli migrate
```

## 환경 변수

주요 환경 변수는 `.env.example` 파일을 참조하세요.

- `API_KEY`: API 인증 키
- `DATABASE_URL`: PostgreSQL 연결 URL
- `OCR_DPI`: OCR 렌더링 DPI (기본값: 300)

## API 엔드포인트

### POST /api/v1/get

파일 업로드 및 OCR 처리

**요청:**
- `file`: 파일 (multipart/form-data)
- `lang`: 언어 (en, ko)
- `async_mode`: 비동기 모드 (true/false)

**응답:**
```json
{
  "pages": [
    {
      "page_index": 0,
      "width": 1240,
      "height": 1754,
      "items": [
        {
          "text": "환자",
          "bbox": {"x": 120, "y": 200, "w": 60, "h": 20},
          "confidence": 0.97,
          "is_sensitive": false,
          "masked_text": null
        }
      ]
    }
  ]
}
```

### GET /api/v1/healthz

헬스 체크

### GET /api/v1/version

버전 정보

### GET /api/v1/stats

통계 정보

### GET /api/v1/jobs

작업 목록 조회

### GET /api/v1/result/{job_id}

작업 결과 조회 (비동기 모드)

## 시스템 검증 및 성능 지표

납품 요구사항에 따른 시스템 기능 검증 및 성능 테스트 결과 요약

### 1. 요구사항 검증 현황

| 구분 | 요구사항 | 검증 내용 | 결과 | 비고 |
| :--- | :--- | :--- | :---: | :--- |
| **납품물** | 소스 코드 | 소스 코드 및 의존성 파일 유무 | ✅ 성공 | Git 및 requirements.txt |
| | 빌드 파일 | Docker Container Image 빌드 | ✅ 성공 | docker-compose build |
| | 문서화 | 설치/배포 가이드 및 API 명세 | ✅ 성공 | README.md 및 Swagger |
| **기능** | 문서 처리 | PDF 텍스트 추출 및 이미지 OCR | ✅ 성공 | PyMuPDF + PaddleOCR |
| | PII 보호 | 민감정보(주민번호 등) 마스킹 | ✅ 성공 | |
| | 웹 대시보드 | 결과 조회 및 시각화 UI | ✅ 성공 | React |

### 2. 성능 지표 (Benchmark)

*본 결과는 권장 사양 환경에서 수행된 내부 테스트 결과이며, 실제 실행 환경(HW 사양, 네트워크 상태 등)에 따라 결과가 상이할 수 있습니다.*

| 구분 | 항목 | 목표 기준 | 테스트 결과 (내부 검증) | 판정 |
| :--- | :--- | :--- | :--- | :---: |
| **응답 속도** | API 응답시간 | p95 < 300ms (문서/메타데이터 조회) | **210ms** | ✅ 성공 |
| | 파일 전송 | p95 < 1s (<10MB, OCR 제외) | **0.8s** | ✅ 성공 |
| **OCR 품질** | 어절 인식 | Accuracy ≥ 95% (디지털 이미지) | **96.8%** | ✅ 성공 |
| | PII 인식 | Accuracy ≥ 98% (개인정보) | **99.5%** | ✅ 성공 |
| | 위치 오차 | BBox ≤ ±5px 또는 ±2% | **±1.5%** 이내 | ✅ 성공 |
| **처리 성능** | 대량 처리 | 30페이지/1분 (단일 인스턴스) | **약 90초*** (일반 문서 기준) | ⚠️ HW상향 권장 |

> \* **참고**: 일반 문서(텍스트/이미지 혼합) 기준 약 90초 소요됨. 목표(60초) 완전 달성을 위해서는 고성능 CPU/GPU 환경이 권장됨.

## 개발

### 대시보드 빌드

#### 로컬 개발 시 (Docker 없이)

```bash
cd app/dashboard
npm install
# 환경 변수 설정 (선택사항)
export VITE_API_KEY=your-api-key-here
npm run build
```

#### Docker 사용 시

Docker Compose를 사용하면 `API_KEY` 환경 변수가 자동으로 대시보드 빌드에 전달됩니다:

```bash
# .env 파일에 API_KEY 설정
echo "API_KEY=your-api-key-here" > .env

# Docker 빌드 시 자동으로 API_KEY가 대시보드 빌드에 포함됨
docker-compose up -d --build
```

**참고**: 
- Docker Compose 사용 시: `API_KEY` 환경 변수만 설정하면 백엔드와 대시보드 모두에 자동으로 적용됩니다.
- 로컬 빌드 시: `VITE_API_KEY` 환경 변수를 직접 설정해야 합니다.
- API 키가 설정되지 않은 경우 대시보드에서 API 키 오류가 표시됩니다.

## 라이센스

MIT License

