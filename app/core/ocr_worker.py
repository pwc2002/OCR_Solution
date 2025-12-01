"""OCR 워커 모듈"""
from paddleocr import PaddleOCR
from typing import List, Dict
import logging
import numpy as np
from PIL import Image
import io
import os  # 추가

# [추가] PaddleOCR/ONNXRuntime이 과도하게 스레드를 점유하지 못하도록 제한
# OCR 프로세스마다 1개의 스레드만 사용하도록 설정 (순차 처리 및 리소스 경합 방지)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

from app.core.pdf_processor import PDFProcessor
from app.core.postprocess import PostProcessor
from app.config.settings import settings
from app.core.pii import PIIDetector  # 추가

logger = logging.getLogger(__name__)


def normalize_lang_code(lang: str) -> str:
    """
    언어 코드를 PaddleOCR에서 사용하는 형식으로 변환
    
    Args:
        lang: 언어 코드 (ko, en만 지원)
        
    Returns:
        PaddleOCR 언어 코드 (korean, en)
    """
    lang_map = {
        "ko": "korean",
        "en": "en",
    }
    return lang_map.get(lang.lower(), "en")  # 기본값은 en


# [추가] 별도 프로세스 실행 함수
def run_ocr_task_in_process(file_bytes: bytes, lang: str, content_type: str) -> List[Dict]:
    """
    별도 프로세스에서 실행될 OCR 작업 함수.
    OCRWorker와 PIIDetector를 내부에서 초기화하여 실행.
    """
    pid = os.getpid()
    logger.info(f"🚀 [Worker Process PID: {pid}] 별도 프로세스에서 OCR 작업 시작")
    
    try:
        # 워커 초기화 (프로세스마다 새로 생성)
        worker = OCRWorker(lang=lang)
        
        # OCR 수행
        results = worker.process_file(file_bytes, content_type)
        
        # PII 탐지 및 마스킹
        pii_detector = PIIDetector()
        for page_result in results:
            page_result['items'] = pii_detector.detect_and_mask(page_result['items'])
            
        return results
    except Exception as e:
        logger.error(f"Process-isolated OCR task failed: {e}", exc_info=True)
        raise e


class OCRWorker:
    """OCR 워커"""
    
    def __init__(self, lang: str = "en", use_angle_cls: bool = True):
        """
        Args:
            lang: 언어 (기본값: en - 영어, 'ko'는 내부적으로 'korean'으로 변환)
            use_angle_cls: 텍스트 방향 분류 사용 여부
        """
        self.lang = lang  # 원본 언어 코드 저장 (DB용)
        # PaddleOCR에서 사용할 언어 코드로 변환
        paddle_lang = normalize_lang_code(lang)
        
        # PaddleOCR 초기화 (PP-OCRv5 설정 반영)
        self.ocr = PaddleOCR(
            lang=paddle_lang,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        self.pdf_processor = PDFProcessor(dpi=settings.ocr_dpi)
        self.postprocessor = PostProcessor()
    
    def process_file(self, file_bytes: bytes, content_type: str = None) -> List[Dict]:
        """
        파일 처리 메인 엔트리포인트 (구조 개선)
        
        Args:
            file_bytes: 파일 바이트 데이터
            content_type: 파일 MIME 타입
            
        Returns:
            페이지별 결과 리스트
        """
        # 1. 파일 type 확인 및 분기
        # 확장자 처리는 호출하는 쪽에서 content-type을 정확히 맞춰주거나, 여기서 확장자를 받을 수 없으므로 
        # routes.py에서 처리된 content_type을 신뢰함.
        if content_type and content_type.startswith("image/"):
            # 1-1. 이미지는 _process_image로 이동
            # 이미지의 경우 width, height를 알기 위해 먼저 열어야 함
            try:
                img = Image.open(io.BytesIO(file_bytes)).convert('RGB')
                width, height = img.size
                
                # 단일 이미지 처리지만 결과 구조 통일을 위해 리스트로 감쌈
                ocr_items = self._process_image(file_bytes, width, height)
                
                # 결과 포맷팅 (단일 페이지)
                page_result = {
                    'page_index': 0,
                    'width': width,
                    'height': height,
                    'items': ocr_items,
                }
                final_results = [page_result]
                
            except Exception as e:
                logger.error(f"이미지 처리 시작 실패: {e}", exc_info=True)
                return []
                
        elif content_type == "application/pdf":
            # 1-2. PDF는 _process_pdf로 이동
            final_results = self._process_pdf(file_bytes)
            
        else:
            # 1-3. 그 외 타입은 처리 중지
            logger.warning(f"지원하지 않는 파일 형식: {content_type}")
            return []
            
        # 2. 결과 필터링 (후처리)
        # 각 페이지별 아이템에 대해 후처리 진행
        for page in final_results:
            if page['items']:
                
                for item in page['items']:
                    item['bbox'] = self.postprocessor.normalize_bbox(
                        item['bbox'],
                        page['width'],
                        page['height']
                    )

        # 3. 결과 리턴
        return final_results

    def _process_pdf(self, pdf_bytes: bytes) -> List[Dict]:
        """
        PDF 처리 내부 로직 (구조 개선)
        
        A. _process_pdf 함수
        1) pdf 에서 텍스트 추출
        2) pdf 에서 이미지 추출(존재한다면)
        3) 각각의 이미지는 _process_image 함수로 이동하여, ocr 진행
        4) 추출한 텍스트와, ocr 결과값을 가지고, 최종 결과 리스트 생성
        """
        # PDFProcessor를 사용하여 텍스트/이미지 추출 (기존 로직 활용)
        pdf_results = self.pdf_processor.process_pdf(pdf_bytes)
        
        final_results = []
        
        # 각 페이지별 처리
        for pdf_page in pdf_results:
            page_result = {
                'page_index': pdf_page['page_index'],
                'width': pdf_page['width'],
                'height': pdf_page['height'],
                'items': [],
            }
            
            # 1) 텍스트 추출 결과 추가
            if pdf_page.get('has_text') and pdf_page.get('text_items'):
                # 텍스트 아이템 추가 (위치 정보 0,0 초기화 - 요청사항)
                for item in pdf_page['text_items']:
                    new_item = item.copy()
                    new_item['bbox'] = {'x': 0, 'y': 0, 'w': 0, 'h': 0}
                    page_result['items'].append(new_item)
            
            # 2) 이미지 추출 및 3) _process_image로 OCR 진행
            if pdf_page.get('images'):
                for img_bytes in pdf_page['images']:
                    ocr_items = self._process_image(
                        img_bytes, 
                        0,
                        0 
                    )
                    page_result['items'].extend(ocr_items)
            
            final_results.append(page_result)
            
        # 페이지 순서 정렬
        final_results.sort(key=lambda x: x['page_index'])
        return final_results

    def _process_image(self, image_bytes: bytes, page_width: int, page_height: int) -> List[Dict]:
        """
        이미지 OCR 처리 내부 로직 (구조 개선)
        
        B. _process_image 함수
        1) 받은 이미지를 paddle ocr 로 ocr 인식 진행 (별도 전처리등 진행하지 않음)
        2) 나온 결과를 정형화 하여, 리턴
        """
        logger.info("Image OCR Processing Start")
        
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            img_array = np.array(img)
            
            ocr_result = self.ocr.predict(img_array) 
            
            items = []
            
            for res in ocr_result:
                if isinstance(res, dict):
                    texts = res.get('rec_texts', [])
                    scores = res.get('rec_scores', [])
                    polys = res.get('dt_polys', [])
                    
                    if texts and scores and len(texts) == len(scores):
                        for i, (text, score) in enumerate(zip(texts, scores)):
                            bbox = {'x': 0, 'y': 0, 'w': 0, 'h': 0}
                            
                            # 좌표 정보 추출 (dt_polys 활용)
                            if polys is not None and len(polys) > i:
                                try:
                                    poly = polys[i]
                                    # numpy array인 경우 리스트로 변환
                                    if hasattr(poly, 'tolist'):
                                        poly = poly.tolist()
                                    if len(poly) >= 4:
                                        xs = [p[0] for p in poly]
                                        ys = [p[1] for p in poly]
                                        x_min = min(xs)
                                        y_min = min(ys)
                                        x_max = max(xs)
                                        y_max = max(ys)
                                        
                                        bbox = {
                                            'x': int(x_min),
                                            'y': int(y_min),
                                            'w': int(x_max - x_min),
                                            'h': int(y_max - y_min)
                                        }
                                except Exception as e:
                                    logger.warning(f"좌표 변환 실패 index={i}: {e}")
                            items.append({
                                'text': text,
                                'bbox': bbox,
                                'confidence': float(score),
                            })
                    else:
                        logger.warning(f"OCR 결과에 텍스트가 없거나 길이가 맞지 않음: {res.keys()}")
            
            logger.info(f"이미지 OCR 완료: {len(items)} 개 항목 추출")
            return items
            
        except Exception as e:
            logger.error(f"이미지 OCR 처리 중 오류: {e}", exc_info=True)
            return []
