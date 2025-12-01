# 멀티스테이지 빌드
FROM python:3.11-slim AS base

# 시스템 패키지 설치 (자주 변경되지 않음, 캐시 최적화)
RUN apt-get update && apt-get install -y \
    libpoppler-cpp-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    wget \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 설치 (requirements.txt 변경 시에만 재빌드)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 대시보드 의존성 설치 (package.json 변경 시에만 재빌드)
# package.json이 변경되지 않으면 npm install은 캐시 사용
COPY app/dashboard/package.json app/dashboard/vite.config.js ./app/dashboard/
WORKDIR /app/app/dashboard
RUN npm install --legacy-peer-deps
# 대시보드 소스 코드 복사 및 빌드
COPY app/dashboard/src/ ./src/
COPY app/dashboard/index.html ./
# 빌드 시 API 키를 환경 변수에서 읽어옴 (ARG를 통해 전달)
ARG VITE_API_KEY
# Create .env file for Vite to pick up the variable
RUN echo "VITE_API_KEY=${VITE_API_KEY}" > .env
RUN npm run build
WORKDIR /app

# 애플리케이션 코드 복사 (자주 변경되는 부분, 마지막에 배치)
# docker-compose.yml에서 볼륨 마운트로 오버라이드되므로 개발 시 재빌드 불필요
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini .
COPY pyproject.toml .

# CLI 명령어 등록을 위해 현재 패키지 설치
RUN pip install .

# 환경 변수 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 포트 노출
EXPOSE 8080

# 실행 명령
CMD ["uvicorn", "app.api.server:app", "--host", "0.0.0.0", "--port", "8080"]

