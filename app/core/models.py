"""데이터베이스 모델"""
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, BigInteger, UUID as SQLUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class Job(Base):
    """작업 모델"""
    __tablename__ = "jobs"
    
    id = Column(SQLUUID, primary_key=True, default=uuid.uuid4)
    api_key = Column(Text, nullable=False)  # 환경변수에서 읽은 키 값 (로그용)
    filename = Column(Text, nullable=False)
    content_type = Column(Text)
    lang = Column(String(2), default="en")  # 고정값: en (영어)
    page_count = Column(Integer, default=0)
    status = Column(String(20), default="queued")  # queued, processing, done, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # 관계
    pages = relationship("Page", back_populates="job", cascade="all, delete-orphan")


class Page(Base):
    """페이지 모델"""
    __tablename__ = "pages"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    job_id = Column(SQLUUID, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    page_index = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    
    # 관계
    job = relationship("Job", back_populates="pages")
    items = relationship("Item", back_populates="page", cascade="all, delete-orphan")


class Item(Base):
    """OCR 아이템 모델"""
    __tablename__ = "items"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    page_id = Column(BigInteger, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    w = Column(Integer, nullable=False)
    h = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False)
    is_sensitive = Column(Boolean, default=False)
    masked_text = Column(Text, nullable=True)
    
    # 관계
    page = relationship("Page", back_populates="items")

