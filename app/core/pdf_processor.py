"""PDF 처리 모듈: 텍스트 레이어 추출 및 이미지 OCR"""
import fitz  # PyMuPDF
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF 처리기: 텍스트 추출 및 이미지 렌더링"""
    
    def __init__(self, dpi: int = 300):
        """
        Args:
            dpi: 이미지 렌더링 DPI
        """
        self.dpi = dpi
        self.zoom = dpi / 72.0  # PyMuPDF는 72 DPI 기준
        self.mat = fitz.Matrix(self.zoom, self.zoom)
    
    def process_pdf(self, pdf_bytes: bytes) -> List[Dict]:
        """
        PDF 처리: 텍스트 레이어 추출 및 이미지 페이지 렌더링
        
        Args:
            pdf_bytes: PDF 바이트 데이터
            
        Returns:
            페이지별 결과 리스트
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        results = []
        
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                result = self._process_page(page, page_num, doc)
                results.append(result)
        finally:
            doc.close()
        
        return results
    
    def _process_page(self, page: fitz.Page, page_index: int, doc: fitz.Document) -> Dict:
        """
        페이지 처리: 텍스트 추출 및 이미지 페이지 판별
        
        Returns:
            {
                'page_index': int,
                'width': int,
                'height': int,
                'has_text': bool,
                'text_items': List[Dict],  # 텍스트 레이어 아이템
                'images': List[bytes],  # 임베딩된 이미지 목록
            }
        """
        # 페이지 크기 (픽셀 단위)
        rect = page.rect
        width = int(rect.width * self.zoom)
        height = int(rect.height * self.zoom)
        
        # 텍스트 레이어 추출
        text_items = self._extract_text_items(page)
        has_text = len(text_items) > 0
        
        # 이미지 추출 (User Request: 페이지 내의 임베딩된 이미지만 추출)
        # 2. 페이지 내의 임베딩된 이미지만 추출 (get_images)
        images = []
        
        # 페이지 내 이미지 목록 가져오기
        image_list = page.get_images()
        
        for img in image_list:
            xref = img[0]
            # 이미지 데이터 추출
            try:
                base_image = doc.extract_image(xref)
                if base_image:
                    images.append(base_image["image"])
            except Exception:
                continue
        
        result = {
            'page_index': page_index,
            'width': width,
            'height': height,
            'has_text': has_text,
            'text_items': text_items,
            'images': images, # 이미지 리스트
        }
        
        return result
    
    def _extract_text_items(self, page: fitz.Page) -> List[Dict]:
        """
        페이지에서 텍스트 아이템 추출
        
        Returns:
            [{
                'text': str,
                'bbox': {'x': int, 'y': int, 'w': int, 'h': int},
                'confidence': float,  # 텍스트 레이어는 1.0
            }]
        """
        items = []
        
        # 텍스트 블록 추출
        blocks = page.get_text("dict")
        
        for block in blocks.get("blocks", []):
            if "lines" not in block:  # 이미지 블록은 건너뜀
                continue
            
            for line in block["lines"]:
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    
                    # bbox를 픽셀 좌표로 변환
                    bbox = span["bbox"]
                    x = int(bbox[0] * self.zoom)
                    y = int(bbox[1] * self.zoom)
                    w = int((bbox[2] - bbox[0]) * self.zoom)
                    h = int((bbox[3] - bbox[1]) * self.zoom)
                    
                    items.append({
                        'text': text,
                        'bbox': {'x': x, 'y': y, 'w': w, 'h': h},
                        'confidence': 1.0,  # 텍스트 레이어는 완벽한 정확도
                    })
        
        return items

