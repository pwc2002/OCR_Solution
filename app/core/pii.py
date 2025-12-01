"""PII 탐지 및 마스킹 모듈: 주민번호, 이름"""
import re
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PIIDetector:
    """PII 탐지 및 마스킹"""
    
    # 주민등록번호 패턴: 6자리-7자리 (하이픈 포함/미포함)
    RRN_PATTERN = re.compile(
        r'\b\d{6}[-]?\d{7}\b'
    )
    
    # 이름 패턴: 한글 2-4음절 (단순 패턴)
    NAME_PATTERN = re.compile(
        r'\b[가-힣]{2,4}\b'
    )
    
    # 이름 주변 컨텍스트 키워드
    NAME_CONTEXT_KEYWORDS = [
        '환자', '성명', '이름', '보호자', '담당자',
        '이름:', '성명:', '환자명:', '이름 :', '성명 :',
    ]
    
    def __init__(self):
        """PII 탐지기 초기화"""
        pass
    
    def detect_and_mask(self, items: List[Dict]) -> List[Dict]:
        """
        아이템 리스트에서 PII 탐지 및 마스킹
        
        Args:
            items: OCR 아이템 리스트 [{'text': str, 'bbox': {...}, ...}]
            
        Returns:
            마스킹된 아이템 리스트 (is_sensitive, masked_text 필드 추가)
        """
        masked_items = []
        
        for item in items:
            text = item['text']
            masked_item = item.copy()
            
            # 주민번호 탐지 및 마스킹
            if self._detect_rrn(text):
                masked_item['is_sensitive'] = True
                masked_item['masked_text'] = self._mask_rrn(text)
                masked_items.append(masked_item)
                continue
            
            # 이름 탐지 및 마스킹 (컨텍스트 기반)
            if self._detect_name_with_context(text, items):
                masked_item['is_sensitive'] = True
                masked_item['masked_text'] = self._mask_name(text)
                masked_items.append(masked_item)
                continue
            
            # PII 없음
            masked_item['is_sensitive'] = False
            masked_item['masked_text'] = None
            masked_items.append(masked_item)
        
        return masked_items
    
    def _detect_rrn(self, text: str) -> bool:
        """주민등록번호 탐지"""
        # 패턴 매칭
        if not self.RRN_PATTERN.search(text):
            return False
        
        # 간단한 유효성 검사 (생년월일 체크는 생략, 패턴만 확인)
        matches = self.RRN_PATTERN.findall(text)
        for match in matches:
            # 하이픈 제거
            rrn = match.replace('-', '')
            if len(rrn) == 13:
                # 첫 6자리는 생년월일 (YYMMDD)
                # 간단한 범위 체크
                try:
                    month = int(rrn[2:4])
                    day = int(rrn[4:6])
                    if 1 <= month <= 12 and 1 <= day <= 31:
                        return True
                except ValueError:
                    continue
        
        return False
    
    def _mask_rrn(self, text: str) -> str:
        """주민등록번호 마스킹"""
        def mask_match(match):
            rrn = match.group(0)
            if '-' in rrn:
                # 하이픈 포함: 123456-1******
                return rrn[:7] + '*' * 6
            else:
                # 하이픈 없음: 1234561******
                return rrn[:7] + '*' * 6
        
        return self.RRN_PATTERN.sub(mask_match, text)
    
    def _detect_name_with_context(self, text: str, all_items: List[Dict]) -> bool:
        """
        이름 탐지 (컨텍스트 기반)
        
        Args:
            text: 탐지할 텍스트
            all_items: 전체 아이템 리스트 (컨텍스트 확인용)
        """
        # 이름 패턴 매칭
        if not self.NAME_PATTERN.match(text.strip()):
            return False
        
        # 컨텍스트 확인: 이름 패턴 앞뒤 아이템에서 키워드 검색
        text_lower = text.lower()
        
        # 현재 아이템 인덱스 찾기
        current_idx = None
        for idx, item in enumerate(all_items):
            if item['text'] == text:
                current_idx = idx
                break
        
        if current_idx is None:
            return False
        
        # 앞뒤 3개 아이템 확인
        context_start = max(0, current_idx - 3)
        context_end = min(len(all_items), current_idx + 4)
        context_items = all_items[context_start:context_end]
        
        # 컨텍스트에서 키워드 검색
        context_text = ' '.join([item['text'] for item in context_items]).lower()
        
        for keyword in self.NAME_CONTEXT_KEYWORDS:
            if keyword.lower() in context_text:
                # 키워드 근처에 이름 패턴이 있으면 이름으로 판단
                keyword_pos = context_text.find(keyword.lower())
                name_pos = context_text.find(text_lower)
                
                # 키워드와 이름 사이 거리 (단어 수)
                distance = abs(context_text[:name_pos].count(' ') - context_text[:keyword_pos].count(' '))
                
                if distance <= 2:  # 2단어 이내
                    return True
        
        return False
    
    def _mask_name(self, text: str) -> str:
        """이름 마스킹"""
        if len(text) <= 2:
            return text[0] + '*'
        elif len(text) == 3:
            return text[0] + text[1] + '*'
        else:  # 4음절
            return text[0] + text[1] + '*' + text[-1]

