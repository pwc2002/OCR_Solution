"""Pydantic 스키마"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class BBox(BaseModel):
    """바운딩 박스"""
    x: int = Field(..., description="X 좌표")
    y: int = Field(..., description="Y 좌표")
    w: int = Field(..., description="너비")
    h: int = Field(..., description="높이")


class Item(BaseModel):
    """OCR 아이템"""
    text: str = Field(..., description="인식된 텍스트")
    bbox: BBox = Field(..., description="바운딩 박스")
    confidence: float = Field(..., ge=0.0, le=1.0, description="신뢰도")
    is_sensitive: bool = Field(..., description="민감정보 여부")
    masked_text: Optional[str] = Field(None, description="마스킹된 텍스트")


class Page(BaseModel):
    """페이지 결과"""
    page_index: int = Field(..., description="페이지 인덱스 (0부터 시작)")
    width: int = Field(..., description="페이지 너비 (픽셀)")
    height: int = Field(..., description="페이지 높이 (픽셀)")
    items: List[Item] = Field(..., description="OCR 아이템 리스트")


class OCRResponse(BaseModel):
    """OCR 응답"""
    pages: List[Page] = Field(..., description="페이지별 결과")


class JobResponse(BaseModel):
    """작업 응답 (비동기 모드)"""
    job_id: str = Field(..., description="작업 ID")
    status: str = Field(..., description="작업 상태")


class ErrorResponse(BaseModel):
    """에러 응답"""
    error: str = Field(..., description="에러 메시지")
    error_code: Optional[str] = Field(None, description="에러 코드")


class JobInfo(BaseModel):
    """작업 정보"""
    id: UUID
    filename: str
    content_type: Optional[str]
    lang: str
    page_count: int
    status: str
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


class StatsResponse(BaseModel):
    """통계 응답"""
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    processing_jobs: int
    avg_processing_time: Optional[float] = None

