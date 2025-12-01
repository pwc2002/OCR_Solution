"""CLI 메인 모듈"""
import typer
from typing import Optional
import uvicorn
from pathlib import Path
import time
import json
import logging
import mimetypes

from app.core.ocr_worker import OCRWorker
from app.core.pii import PIIDetector
from app.core.dao import init_db
from app.config.settings import settings

app = typer.Typer(help="의료 문서 OCR 시스템 CLI")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_content_type(file_path: Path) -> str:
    """파일 확장자로 MIME 타입 추론"""
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        return mime_type
    
    # mimetypes가 못 찾을 경우 확장자로 하드코딩
    ext = file_path.suffix.lower()
    if ext == '.pdf':
        return 'application/pdf'
    elif ext in ['.jpg', '.jpeg']:
        return 'image/jpeg'
    elif ext == '.png':
        return 'image/png'
    elif ext == '.bmp':
        return 'image/bmp'
    elif ext == '.tiff':
        return 'image/tiff'
    return 'application/octet-stream'


@app.command()
def run(
    file: Path = typer.Argument(..., help="처리할 파일 경로 (PDF, 이미지)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="출력 파일 경로 (JSON)"),
    lang: str = typer.Option("ko", "--lang", help="OCR 언어 (기본값: ko)"),
    pii: bool = typer.Option(True, "--pii", "--no-pii", help="PII(개인정보) 마스킹 수행 여부"),
):
    """로컬에서 파일 OCR 및 PII 처리"""
    if not file.exists():
        typer.echo(f"파일을 찾을 수 없습니다: {file}", err=True)
        raise typer.Exit(1)
    
    content_type = get_content_type(file)
    typer.echo(f"파일 처리 중: {file} (Type: {content_type}, Lang: {lang})")
    
    try:
        # 1. 파일 읽기
        with open(file, "rb") as f:
            file_bytes = f.read()
        
        # 2. OCR 처리
        ocr_worker = OCRWorker(lang=lang)
        # process_file은 페이지별 결과 리스트를 반환함
        results = ocr_worker.process_file(file_bytes, content_type=content_type)
        
        # 3. PII 탐지 및 마스킹 (옵션)
        if pii:
            typer.echo("PII 탐지 및 마스킹 수행 중...")
            pii_detector = PIIDetector()
            for page_result in results:
                page_result['items'] = pii_detector.detect_and_mask(page_result['items'])
        
        # 4. 결과 정리 (JSON 직렬화를 위해 필요한 필드만 추출)
        output_data = {
            "meta": {
                "filename": file.name,
                "content_type": content_type,
                "lang": lang,
                "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_pages": len(results)
            },
            "pages": [
                {
                    "page_index": page.get("page_index", i),
                    "width": page["width"],
                    "height": page["height"],
                    "items": [
                        {
                            "text": item["text"],
                            "bbox": item["bbox"],
                            "confidence": item["confidence"],
                            "is_sensitive": item.get("is_sensitive", False),
                            "masked_text": item.get("masked_text"),
                        }
                        for item in page["items"]
                    ],
                }
                for i, page in enumerate(results)
            ]
        }
        
        # 5. 출력
        if output:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            typer.echo(f"결과 저장 완료: {output}")
        else:
            print(json.dumps(output_data, ensure_ascii=False, indent=2))
        
    except Exception as e:
        typer.echo(f"오류 발생: {e}", err=True)
        logger.exception("처리 중 상세 오류")
        raise typer.Exit(1)


@app.command()
def server(
    host: str = typer.Option(settings.host, "--host", "-h", help="호스트"),
    port: int = typer.Option(settings.port, "--port", "-p", help="포트"),
    reload: bool = typer.Option(False, "--reload", help="자동 리로드"),
    workers: int = typer.Option(1, "--workers", "-w", help="워커 프로세스 수"),
):
    """API 서버 실행"""
    typer.echo(f"서버 시작: http://{host}:{port} (Workers: {workers})")
    uvicorn.run(
        "app.api.server:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers
    )


@app.command()
def migrate():
    """데이터베이스 초기화 및 마이그레이션"""
    typer.echo("데이터베이스 초기화 중...")
    try:
        init_db()
        typer.echo("초기화 완료.")
    except Exception as e:
        typer.echo(f"오류 발생: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
