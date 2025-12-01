"""애플리케이션 설정"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # API 설정
    api_key: str
    api_key_header: str = "Authorization"
    
    # 데이터베이스
    database_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # OCR 설정
    ocr_workers: int = 2  # 4 vCore 환경 최적화 (기본값 4 -> 2)
    ocr_max_queue: int = 30  # 30페이지 처리 목표에 맞춤
    ocr_dpi: int = 300
    ocr_model_dir: str = "/app/models"
    paddleocr_home: str = "/root/.paddleocr"
    
    # 성능 최적화 설정
    ocr_parallel_pages: int = 2  # 페이지 병렬 처리 수 (CPU 코어 절반)
    ocr_max_image_size: int = 4096  # 이미지 최대 크기 제한
    ocr_enable_ppstructure: bool = False  # 표 인식 비활성화 (필요 시 true)
    
    # 파일 설정
    max_file_size_mb: int = 10
    
    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"
    
    # 애플리케이션
    app_name: str = "mediview"
    app_version: str = "0.1.0"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# 전역 설정 인스턴스
settings = Settings()
