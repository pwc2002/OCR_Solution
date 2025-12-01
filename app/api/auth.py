"""인증 모듈: API Key 검증"""
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from typing import Optional
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)

# API Key 헤더
api_key_header = APIKeyHeader(name=settings.api_key_header, auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    API Key 검증
    
    Args:
        api_key: 요청 헤더의 API Key
        
    Returns:
        검증된 API Key
        
    Raises:
        HTTPException: API Key가 유효하지 않은 경우
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key가 필요합니다",
        )
    
    # 환경변수와 단순 비교
    if api_key != settings.api_key:
        logger.warning(f"잘못된 API Key 시도: {api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 API Key",
        )
    
    return api_key

