"""API 라우트"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request, status, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, List, Union
from uuid import UUID
import logging
from datetime import datetime
import asyncio
from concurrent.futures import ProcessPoolExecutor

from app.api.auth import verify_api_key
from app.api.schemas import (
    OCRResponse, JobResponse, ErrorResponse, JobInfo, StatsResponse, Page, Item, BBox
)
# run_ocr_task_in_process 임포트
from app.core.ocr_worker import OCRWorker, run_ocr_task_in_process
from app.core.pii import PIIDetector
from app.core.dao import get_db_session, JobDAO, PageDAO, ItemDAO, SessionLocal
from app.core.models import Job
from app.config.settings import settings
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()

# 1. 전역 실행기 생성 (max_workers=1로 설정하여 순차 처리 강제)
# 순차 처리하지만 별도 프로세스이므로 메인 스레드 블로킹 방지 -> health check 가능
_ocr_executor = ProcessPoolExecutor(max_workers=1)
_pii_detector = PIIDetector()


# def get_ocr_worker(lang: str = "en") -> OCRWorker:
#     """OCR 워커 가져오기 (언어별로 워커 풀 관리)"""
#     # 이제 직접 호출하지 않고 run_in_executor를 통해 별도 프로세스에서 실행하므로 주석 처리
#     return OCRWorker(lang=lang)


@router.post("/get", response_model=Union[OCRResponse, JobResponse])
async def process_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    lang: Optional[str] = Form("en"),
    async_mode: Optional[str] = Form(None),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db_session),
):
    """
    파일 OCR 처리
    
    - **file**: 업로드할 파일 (PDF 또는 이미지)
    - **lang**: 언어 코드 (en, ko만 지원, 기본값: en)
    - **async_mode**: 비동기 모드 (true인 경우 job_id만 반환)
    """
    try:
        # 파일 검증
        if not file.filename:
            raise HTTPException(status_code=400, detail="파일이 필요합니다")
        
        # 파일 확장자 검증 (pdf, png, jpeg만 허용)
        filename_lower = file.filename.lower()
        allowed_extensions = ['.pdf', '.png', '.jpeg', '.jpg']
        if not any(filename_lower.endswith(ext) for ext in allowed_extensions):
            raise HTTPException(
                status_code=400,
                detail="지원하지 않는 파일 형식입니다. PDF, PNG, JPEG만 업로드 가능합니다"
            )
        
        # 언어 검증 (en, ko만 허용, 기본값 en)
        if not lang:
            lang = "en"
        lang = lang.lower()
        if lang not in ["en", "ko"]:
            raise HTTPException(
                status_code=400,
                detail="지원하지 않는 언어입니다. 'en' 또는 'ko'만 사용 가능합니다"
            )
        
        # 파일 크기 확인
        file_bytes = await file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)
        if file_size_mb > settings.max_file_size_mb:
            raise HTTPException(
                status_code=400,
                detail=f"파일 크기는 {settings.max_file_size_mb}MB 이하여야 합니다"
            )
        
        # 작업 생성
        job = JobDAO.create(
            db=db,
            api_key=api_key,
            filename=file.filename,
            content_type=file.content_type,
            lang=lang,
        )
        job_id = job.id
        
        # 비동기 모드 (async_mode가 "true" 문자열이면 활성화)
        is_async = async_mode and async_mode.lower() == "true"
        if is_async:
            # 작업 생성 커밋만 수행 (최소한의 DB 작업)
            db.commit()
            
            # 백그라운드 작업: OCR 처리
            background_tasks.add_task(process_job_async, job_id, file_bytes, lang)
            
            # 즉시 반환 (작업 생성 후 바로 응답)
            return JobResponse(job_id=str(job_id), status="queued")
        
        # 동기 모드: 즉시 처리
        try:
            JobDAO.update_status(db, job_id, "processing")
            db.commit()
            
            # 파일 확장자로 타입 확인 (pdf, png, jpeg만 허용)
            filename = file.filename.lower() if file.filename else ""
            content_type = file.content_type
            
            # content_type 보정
            if filename.endswith('.pdf'):
                content_type = "application/pdf"
            elif filename.endswith(('.png', '.jpg', '.jpeg')):
                content_type = "image/png"
            else:
                raise HTTPException(
                    status_code=400,
                    detail="지원하지 않는 파일 형식입니다. PDF, PNG, JPEG만 업로드 가능합니다"
                )

            # OCR 처리 (순차적이지만 별도 프로세스에서 실행)
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(
                _ocr_executor,
                run_ocr_task_in_process,
                file_bytes,
                lang,
                content_type
            )
            
            # PII 탐지 및 마스킹은 worker 내부에서 수행됨
            
            # DB 저장
            save_results_to_db(db, job_id, results)
            
            # 작업 완료
            JobDAO.update_status(db, job_id, "done", page_count=len(results))
            db.commit()
            
            # 응답 생성
            response_pages = []
            for page_result in results:
                items = [
                    Item(
                        text=item['text'],
                        bbox=BBox(**item['bbox']),
                        confidence=item['confidence'],
                        is_sensitive=item['is_sensitive'],
                        masked_text=item.get('masked_text'),
                    )
                    for item in page_result['items']
                ]
                response_pages.append(
                    Page(
                        page_index=page_result['page_index'],
                        width=page_result['width'],
                        height=page_result['height'],
                        items=items,
                    )
                )
            
            return OCRResponse(pages=response_pages)
        
        except Exception as e:
            logger.error(f"OCR 처리 중 오류: {e}", exc_info=True)
            JobDAO.update_status(db, job_id, "failed", error_message=str(e))
            db.commit()
            raise HTTPException(status_code=500, detail=f"OCR 처리 중 오류가 발생했습니다: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"요청 처리 중 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="내부 서버 오류")


async def process_job_async(job_id: UUID, file_bytes: bytes, lang: str = "en"):
    """비동기 작업 처리"""
    db = SessionLocal()
    try:
        # job에서 lang 정보 가져오기 (혹시 모를 경우를 대비해 기본값 사용)
        job = JobDAO.get_by_id(db, job_id)
        if job and job.lang:
            lang = job.lang
        
        JobDAO.update_status(db, job_id, "processing")
        db.commit()
        
        # 파일 확장자로 타입 확인 (pdf, png, jpeg만 허용)
        filename = job.filename.lower() if job.filename else ""
        content_type = job.content_type
        
        if filename.endswith('.pdf'):
             content_type = "application/pdf"
        elif filename.endswith(('.png', '.jpg', '.jpeg')):
             content_type = "image/png"
        else:
             # 지원하지 않는 파일 형식
             raise ValueError(f"지원하지 않는 파일 형식입니다: {filename}")

        # OCR 처리 (순차적 실행)
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(
            _ocr_executor,
            run_ocr_task_in_process,
            file_bytes,
            lang,
            content_type
        )
        
        # DB 저장
        save_results_to_db(db, job_id, results)
        
        # 작업 완료
        JobDAO.update_status(db, job_id, "done", page_count=len(results))
        db.commit()
    
    except Exception as e:
        logger.error(f"비동기 작업 처리 중 오류: {e}", exc_info=True)
        db.rollback()
        try:
            JobDAO.update_status(db, job_id, "failed", error_message=str(e))
            db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def save_results_to_db(db: Session, job_id: UUID, results: List[dict]):
    """결과를 DB에 저장"""
    for page_result in results:
        # 페이지 생성
        page = PageDAO.create(
            db=db,
            job_id=job_id,
            page_index=page_result['page_index'],
            width=page_result['width'],
            height=page_result['height'],
        )
        
        # 아이템 생성
        items = []
        for item in page_result['items']:
            items.append({
                'page_id': page.id,
                'text': item['text'],
                'x': item['bbox']['x'],
                'y': item['bbox']['y'],
                'w': item['bbox']['w'],
                'h': item['bbox']['h'],
                'confidence': item['confidence'],
                'is_sensitive': item['is_sensitive'],
                'masked_text': item.get('masked_text'),
            })
        
        if items:
            ItemDAO.create_bulk(db, items)


@router.get("/healthz")
async def health_check():
    """헬스 체크"""
    return {"status": "ok"}


@router.get("/version")
async def get_version():
    """버전 정보"""
    return {
        "version": settings.app_version,
        "name": settings.app_name,
    }


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db_session),
):
    """통계 정보"""
    all_jobs = JobDAO.list_jobs(db, limit=10000)
    
    total_jobs = len(all_jobs)
    completed_jobs = len([j for j in all_jobs if j.status == "done"])
    failed_jobs = len([j for j in all_jobs if j.status == "failed"])
    processing_jobs = len([j for j in all_jobs if j.status == "processing"])
    
    # 평균 처리 시간 계산
    completed_with_time = [j for j in all_jobs if j.status == "done" and j.completed_at]
    avg_time = None
    if completed_with_time:
        times = [
            (j.completed_at - j.created_at).total_seconds()
            for j in completed_with_time
        ]
        avg_time = sum(times) / len(times) if times else None
    
    return StatsResponse(
        total_jobs=total_jobs,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        processing_jobs=processing_jobs,
        avg_processing_time=avg_time,
    )


@router.get("/jobs", response_model=List[JobInfo])
async def list_jobs(
    limit: int = 100,
    status: Optional[str] = None,
    from_ts: Optional[datetime] = None,
    to_ts: Optional[datetime] = None,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db_session),
):
    """작업 목록 조회"""
    jobs = JobDAO.list_jobs(db, limit=limit, status=status, from_ts=from_ts, to_ts=to_ts)
    return [JobInfo(**job.__dict__) for job in jobs]


@router.get("/result/{job_id}", response_model=OCRResponse)
async def get_result(
    job_id: UUID,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db_session),
):
    """작업 결과 조회 (비동기 모드)"""
    job = JobDAO.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    if job.status == "queued" or job.status == "processing":
        raise HTTPException(status_code=202, detail="작업이 아직 진행 중입니다")
    
    if job.status == "failed":
        raise HTTPException(status_code=500, detail=f"작업 실패: {job.error_message}")
    
    # DB에서 결과 조회
    pages = PageDAO.get_by_job_id(db, job_id)
    
    response_pages = []
    for page in pages:
        items = ItemDAO.get_by_page_id(db, page.id)
        item_schemas = [
            Item(
                text=item.text,
                bbox=BBox(x=item.x, y=item.y, w=item.w, h=item.h),
                confidence=item.confidence,
                is_sensitive=item.is_sensitive,
                masked_text=item.masked_text,
            )
            for item in items
        ]
        response_pages.append(
            Page(
                page_index=page.page_index,
                width=page.width,
                height=page.height,
                items=item_schemas,
            )
        )
    
    return OCRResponse(pages=response_pages)
