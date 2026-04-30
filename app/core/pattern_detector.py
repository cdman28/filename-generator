"""
파일명에서 날짜 패턴을 자동으로 감지합니다.

지원 패턴:
  - YYMMDD  : 6자리 숫자 (예: 260503)  → 주 단위
  - YYYY-N월 : (예: 2026-4월)           → 월 단위
  - YYYY년 N월: (예: 2026년 5월)        → 월 단위
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


# ─── 패턴 정의 ───────────────────────────────────────────────────────────────
# (이름, 정규식, 주기)
DATE_PATTERNS = [
    ("YYYY년 N월", re.compile(r"\d{4}년\s*\d{1,2}월"), "monthly"),
    ("YYYY-N월",   re.compile(r"\d{4}-\d{1,2}월"),      "monthly"),
    ("YYMMDD",     re.compile(r"\b\d{6}\b"),             "weekly"),
]


@dataclass
class DetectedPattern:
    pattern_name: str          # 예: "YYMMDD"
    cycle: str                 # "weekly" | "monthly"
    regex: re.Pattern          # 감지에 쓰인 정규식
    matched_text: str          # 파일명에서 실제로 매칭된 날짜 텍스트
    confidence: float          # 0.0 ~ 1.0 (같은 패턴 파일 비율)


@dataclass
class FilePatternInfo:
    filename: str
    pattern: Optional[DetectedPattern] = None
    # 패턴 감지 실패 시 None


def detect_pattern_in_name(stem: str) -> Optional[DetectedPattern]:
    """파일명(확장자 제외)에서 날짜 패턴 하나를 감지합니다."""
    for name, regex, cycle in DATE_PATTERNS:
        match = regex.search(stem)
        if match:
            return DetectedPattern(
                pattern_name=name,
                cycle=cycle,
                regex=regex,
                matched_text=match.group(),
                confidence=1.0,
            )
    return None


def scan_folder(folder_path: str) -> List[FilePatternInfo]:
    """
    폴더 내 파일 목록을 스캔하여 각 파일의 날짜 패턴 정보를 반환합니다.
    하위 폴더는 탐색하지 않습니다.
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        return []

    results: List[FilePatternInfo] = []
    pattern_count: dict = {}  # pattern_name → count

    # 최근 수정일(mtime) 기준 내림차순 정렬 → 가장 최근 파일이 앞에 오도록
    raw: List[Tuple[str, Optional[DetectedPattern]]] = []
    try:
        entries = sorted(
            (e for e in folder.iterdir() if e.is_file()),
            key=lambda e: e.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        entries = []
    for entry in entries:
        if not entry.is_file():
            continue
        stem = entry.stem
        detected = detect_pattern_in_name(stem)
        raw.append((entry.name, detected))
        if detected:
            pattern_count[detected.pattern_name] = (
                pattern_count.get(detected.pattern_name, 0) + 1
            )

    total = len(raw)
    for filename, detected in raw:
        if detected and total > 0:
            detected.confidence = pattern_count[detected.pattern_name] / total
        results.append(FilePatternInfo(filename=filename, pattern=detected))

    return results


def replace_date_in_name(filename: str, new_date_text: str) -> str:
    """
    파일명(확장자 포함)에서 감지된 날짜 부분을 new_date_text로 교체합니다.
    패턴이 감지되지 않으면 원본 파일명을 그대로 반환합니다.
    """
    stem = Path(filename).stem
    suffix = Path(filename).suffix

    detected = detect_pattern_in_name(stem)
    if detected is None:
        return filename

    new_stem = detected.regex.sub(new_date_text, stem, count=1)
    return new_stem + suffix


def format_date_text(pattern_name: str, cycle: str, target_date) -> str:
    """
    DateCalculator가 반환하는 date 객체를 패턴 이름에 맞는 텍스트로 변환합니다.
    target_date: datetime.date
    """
    if pattern_name == "YYMMDD":
        # 260503 형식: YY=연도 뒤 2자리
        yy = str(target_date.year)[2:]
        return f"{yy}{target_date.month:02d}{target_date.day:02d}"
    elif pattern_name == "YYYY-N월":
        return f"{target_date.year}-{target_date.month}월"
    elif pattern_name == "YYYY년 N월":
        return f"{target_date.year}년 {target_date.month}월"
    # 알 수 없는 패턴이면 빈 문자열
    return ""
