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

