"""데이터베이스 접근 레이어"""
from sqlalchemy import create_engine, Index
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator, Optional, List
from uuid import UUID
from datetime import datetime

from app.core.models import Base, Job, Page, Item
from app.config.settings import settings


# 데이터베이스 엔진 생성
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
    echo=False,
)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """데이터베이스 초기화 (테이블 생성)"""
    Base.metadata.create_all(bind=engine)
    
    # 인덱스 생성
    Index("idx_jobs_status", Job.status).create(bind=engine, checkfirst=True)
    Index("idx_pages_job", Page.job_id).create(bind=engine, checkfirst=True)
    Index("idx_items_page", Item.page_id).create(bind=engine, checkfirst=True)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """데이터베이스 세션 컨텍스트 매니저"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency용 데이터베이스 세션"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class JobDAO:
    """작업 DAO"""
    
    @staticmethod
    def create(
        db: Session,
        api_key: str,
        filename: str,
        content_type: Optional[str] = None,
        lang: str = "ko",
    ) -> Job:
        """작업 생성"""
        job = Job(
            api_key=api_key,
            filename=filename,
            content_type=content_type,
            lang=lang,
            status="queued",
        )
        db.add(job)
        db.flush()
        return job
    
    @staticmethod
    def get_by_id(db: Session, job_id: UUID) -> Optional[Job]:
        """작업 ID로 조회"""
        return db.query(Job).filter(Job.id == job_id).first()
    
    @staticmethod
    def update_status(
        db: Session,
        job_id: UUID,
        status: str,
        error_message: Optional[str] = None,
        page_count: Optional[int] = None,
    ) -> Optional[Job]:
        """작업 상태 업데이트"""
        job = JobDAO.get_by_id(db, job_id)
        if job:
            job.status = status
            if error_message:
                job.error_message = error_message
            if page_count is not None:
                job.page_count = page_count
            if status in ("done", "failed"):
                job.completed_at = datetime.utcnow()
            db.flush()
        return job
    
    @staticmethod
    def list_jobs(
        db: Session,
        limit: int = 100,
        status: Optional[str] = None,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
    ) -> List[Job]:
        """작업 목록 조회"""
        query = db.query(Job)
        if status:
            query = query.filter(Job.status == status)
        if from_ts:
            query = query.filter(Job.created_at >= from_ts)
        if to_ts:
            query = query.filter(Job.created_at <= to_ts)
        return query.order_by(Job.created_at.desc()).limit(limit).all()


class PageDAO:
    """페이지 DAO"""
    
    @staticmethod
    def create(
        db: Session,
        job_id: UUID,
        page_index: int,
        width: int,
        height: int,
    ) -> Page:
        """페이지 생성"""
        page = Page(
            job_id=job_id,
            page_index=page_index,
            width=width,
            height=height,
        )
        db.add(page)
        db.flush()
        return page
    
    @staticmethod
    def get_by_job_id(db: Session, job_id: UUID) -> List[Page]:
        """작업 ID로 페이지 목록 조회"""
        return db.query(Page).filter(Page.job_id == job_id).order_by(Page.page_index).all()


class ItemDAO:
    """아이템 DAO"""
    
    @staticmethod
    def create_bulk(
        db: Session,
        items: List[dict],
    ) -> List[Item]:
        """아이템 일괄 생성"""
        item_objects = [Item(**item) for item in items]
        db.bulk_save_objects(item_objects)
        db.flush()
        return item_objects
    
    @staticmethod
    def get_by_page_id(db: Session, page_id: int) -> List[Item]:
        """페이지 ID로 아이템 목록 조회"""
        return db.query(Item).filter(Item.page_id == page_id).all()

