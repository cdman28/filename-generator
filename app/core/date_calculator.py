"""
주 단위 / 월 단위 날짜를 계산합니다.

- weekly  : 기준 날짜에서 +7일
- monthly : 기준 날짜의 다음 달 1일 (연말 12월 → 다음 해 1월 자동 처리)
"""

from datetime import date, timedelta
from collections import Counter
from typing import List


def next_weekly(base: date) -> date:
    """기준 날짜에서 정확히 7일 뒤 날짜를 반환합니다."""
    return base + timedelta(days=7)


def next_monthly(base: date) -> date:
    """
    기준 날짜의 다음 달 1일을 반환합니다.
    예) 2026-04-xx → 2026-05-01
        2026-12-xx → 2027-01-01
    """
    if base.month == 12:
        return date(base.year + 1, 1, 1)
    return date(base.year, base.month + 1, 1)


def suggest_next_date(cycle: str, base: date = None) -> date:
    """
    cycle ("weekly" | "monthly") 과 기준 날짜를 받아 다음 생성 날짜를 반환합니다.
    base가 None이면 오늘 날짜를 사용합니다.
    """
    if base is None:
        base = date.today()
    if cycle == "weekly":
        return next_weekly(base)
    elif cycle == "monthly":
        return next_monthly(base)
    raise ValueError(f"알 수 없는 주기: {cycle}")


def parse_date_from_text(pattern_name: str, text: str) -> date | None:
    """
    패턴 이름과 파일명에서 추출된 날짜 텍스트를 파싱하여 date 객체를 반환합니다.
    파싱 실패 시 None을 반환합니다.
    """
    import re

    try:
        if pattern_name == "YYMMDD":
            # 예: "260503" → 2026-05-03
            if len(text) == 6 and text.isdigit():
                yy = int(text[0:2])
                mm = int(text[2:4])
                dd = int(text[4:6])
                year = 2000 + yy
                return date(year, mm, dd)

        elif pattern_name == "YYYY-N월":
            # 예: "2026-4월" → 2026-04-01
            m = re.match(r"(\d{4})-(\d{1,2})월", text)
            if m:
                return date(int(m.group(1)), int(m.group(2)), 1)

        elif pattern_name == "YYYY년 N월":
            # 예: "2026년 5월" → 2026-05-01
            m = re.match(r"(\d{4})년\s*(\d{1,2})월", text)
            if m:
                return date(int(m.group(1)), int(m.group(2)), 1)

    except (ValueError, AttributeError):
        return None

    return None


def infer_next_date(dates: List[date]) -> date | None:
    """
    날짜 목록을 분석하여 다음 날짜를 추론합니다.

    - 날짜들을 정렬하고 간격(days)의 최빈값을 계산합니다.
    - 간격이 25~35일이면 월 단위로 판단하여 next_monthly를 사용합니다.
    - 그 외에는 마지막 날짜 + 최빈 간격을 반환합니다.
    - 날짜가 1개뿐이면 사이클 추론 불가 → 7일 뒤를 반환합니다.
    """
    if not dates:
        return None

    sorted_dates = sorted(set(dates))

    if len(sorted_dates) == 1:
        return sorted_dates[0] + timedelta(days=7)

    gaps = [
        (sorted_dates[i + 1] - sorted_dates[i]).days
        for i in range(len(sorted_dates) - 1)
    ]
    gaps = [g for g in gaps if g > 0]
    if not gaps:
        return sorted_dates[-1] + timedelta(days=7)

    most_common_gap = Counter(gaps).most_common(1)[0][0]
    last_date = sorted_dates[-1]

    if 25 <= most_common_gap <= 35:
        return next_monthly(last_date)

    return last_date + timedelta(days=most_common_gap)
