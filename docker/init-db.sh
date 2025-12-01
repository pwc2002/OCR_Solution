#!/bin/bash
set -e

echo "데이터베이스 초기화 시작..."

# 데이터베이스 연결 대기
until pg_isready -h postgres -U postgres; do
  echo "PostgreSQL이 준비될 때까지 대기 중..."
  sleep 2
done

echo "데이터베이스 연결 성공"

# 마이그레이션 실행
python -m alembic upgrade head

echo "데이터베이스 초기화 완료"

