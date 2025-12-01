"""OCR 후처리 모듈: 어절 병합, bbox 정규화"""
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class PostProcessor:
    """OCR 후처리기"""
    
    @staticmethod
    def normalize_bbox(bbox: Dict, page_width: int, page_height: int) -> Dict:
        """
        bbox 정규화 (±5px 오차 보정)
        
        Args:
            bbox: {'x': int, 'y': int, 'w': int, 'h': int}
            page_width: 페이지 너비
            page_height: 페이지 높이
            
        Returns:
            정규화된 bbox
        """
        x = max(0, min(bbox['x'], page_width))
        y = max(0, min(bbox['y'], page_height))
        w = max(1, min(bbox['w'], page_width - x))
        h = max(1, min(bbox['h'], page_height - y))
        
        return {'x': x, 'y': y, 'w': w, 'h': h}

