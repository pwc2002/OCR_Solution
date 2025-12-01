"""FastAPI 서버 엔트리"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
import time
import sys  # sys 모듈 추가 필요

from app.api.routes import router
from app.config.settings import settings
from app.core.dao import init_db

# 로깅 설정 (기존 basicConfig 대신 아래 내용으로 교체)
# Uvicorn이 로거 설정을 가로채는 것을 방지하기 위해 루트 로거를 직접 설정
logger = logging.getLogger()
logger.setLevel(getattr(logging, settings.log_level))

# 핸들러가 없을 때만 추가 (중복 방지)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - [PID:%(process)d] -  %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

# 'app' 패키지 하위의 모든 로그도 이 레벨을 따르도록 명시적 설정
logging.getLogger("app").setLevel(getattr(logging, settings.log_level))

logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="의료 문서 OCR 시스템",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 요청 시간 측정 미들웨어
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"예상치 못한 오류: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "내부 서버 오류", "error_code": "INTERNAL_ERROR"},
    )


# 정적 파일 서빙 (대시보드) - 라우터 등록 전에 설정
import os
from pathlib import Path
from fastapi.responses import FileResponse, RedirectResponse

# 여러 경로에서 대시보드 dist 찾기
dashboard_paths = [
    # 볼륨 마운트 후 로컬 경로 (개발 모드)
    os.path.join("/app", "app", "dashboard", "dist"),
    # Docker 빌드 경로 (프로덕션 모드)
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "dist"),
    # 현재 작업 디렉토리 기준
    os.path.join(os.getcwd(), "app", "dashboard", "dist"),
]

dashboard_path = None
for path in dashboard_paths:
    full_path = Path(path)
    if full_path.exists() and full_path.is_dir():
        # index.html 파일 확인
        index_file = full_path / "index.html"
        if index_file.exists():
            dashboard_path = str(full_path.resolve())
            break

if dashboard_path:
    # 대시보드 정적 파일 마운트
    app.mount("/dashboard", StaticFiles(directory=dashboard_path, html=True), name="dashboard")
    logger.info(f"대시보드 정적 파일 서빙: {dashboard_path}")
    
    # /dashboard 경로 접근 시 index.html 제공 (리다이렉트 대신 직접 제공)
    @app.get("/dashboard")
    async def dashboard_root():
        """대시보드 루트 경로"""
        index_path = os.path.join(dashboard_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return RedirectResponse(url="/dashboard/")
else:
    logger.warning(f"대시보드 정적 파일을 찾을 수 없습니다. 확인한 경로: {dashboard_paths}")
    logger.warning("대시보드를 사용하려면: cd app/dashboard && npm install && npm run build")

# 라우터 등록 (대시보드 마운트 후)
app.include_router(router, prefix="/api/v1", tags=["OCR"])

# 루트 경로는 대시보드로 리다이렉트
@app.get("/")
async def root():
    """루트 경로는 대시보드로 리다이렉트"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard/")


@app.on_event("startup")
async def startup_event():
    """시작 시 실행"""
    logger.info(f"{settings.app_name} v{settings.app_version} 시작")
    
    # 데이터베이스 초기화
    try:
        init_db()
        logger.info("데이터베이스 초기화 완료")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """종료 시 실행"""
    logger.info(f"{settings.app_name} 종료")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )

