"""
원본 파일을 복사하고 파일명의 날짜 부분을 새 날짜로 치환합니다.
"""

import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List

from app.core.pattern_detector import (
    DetectedPattern,
    detect_pattern_in_name,
    format_date_text,
    replace_date_in_name,
)
from app.core.date_calculator import parse_date_from_text, suggest_next_date


@dataclass
class GenerationPlan:
    """생성 예정 파일 하나의 계획 정보."""
    source_path: str       # 원본 파일 전체 경로
    new_filename: str      # 새 파일명 (경로 제외)
    new_full_path: str     # 새 파일 전체 경로
    pattern_name: str      # 감지된 패턴 이름
    cycle: str             # "weekly" | "monthly"
    target_date: date      # 새로 생성될 날짜
    already_exists: bool   # 같은 이름의 파일이 이미 존재하는지


@dataclass
class GenerationResult:
    """파일 생성 결과 하나."""
    source_path: str
    new_full_path: str
    success: bool
    message: str           # 성공 메시지 또는 오류 메시지


def build_plan(
    source_path: str,
    target_date: date,
    override_pattern: DetectedPattern = None,
) -> GenerationPlan | None:
    """
    원본 파일 경로와 대상 날짜를 받아 GenerationPlan을 구성합니다.
    패턴 감지 실패 시 None 반환.
    override_pattern을 지정하면 자동 감지를 건너뜁니다.
    """
    src = Path(source_path)
    detected = override_pattern or detect_pattern_in_name(src.stem)
    if detected is None:
        return None

    new_date_text = format_date_text(detected.pattern_name, detected.cycle, target_date)
    if not new_date_text:
        return None

    new_filename = replace_date_in_name(src.name, new_date_text)
    new_full_path = str(src.parent / new_filename)

    return GenerationPlan(
        source_path=source_path,
        new_filename=new_filename,
        new_full_path=new_full_path,
        pattern_name=detected.pattern_name,
        cycle=detected.cycle,
        target_date=target_date,
        already_exists=Path(new_full_path).exists(),
    )


def build_plans_for_folder(
    selected_files: List[str],
    target_date: date,
) -> List[GenerationPlan]:
    """
    선택된 파일 목록에 대해 GenerationPlan 목록을 구성합니다.
    패턴 감지 실패 파일은 결과에서 제외합니다.
    """
    plans = []
    for filepath in selected_files:
        plan = build_plan(filepath, target_date)
        if plan is not None:
            plans.append(plan)
    return plans


def execute_plans(
    plans: List[GenerationPlan],
    overwrite: bool = False,
) -> List[GenerationResult]:
    """
    GenerationPlan 목록을 실행하여 파일을 복사·생성합니다.

    overwrite=False이면 이미 존재하는 파일은 건너뛰고 실패로 표시합니다.
    """
    results = []
    for plan in plans:
        src = Path(plan.source_path)
        dst = Path(plan.new_full_path)

        if not src.exists():
            results.append(GenerationResult(
                source_path=plan.source_path,
                new_full_path=plan.new_full_path,
                success=False,
                message=f"원본 파일을 찾을 수 없습니다: {src.name}",
            ))
            continue

        if dst.exists() and not overwrite:
            results.append(GenerationResult(
                source_path=plan.source_path,
                new_full_path=plan.new_full_path,
                success=False,
                message=f"이미 존재하는 파일입니다: {dst.name}",
            ))
            continue

        try:
            shutil.copy2(str(src), str(dst))
            results.append(GenerationResult(
                source_path=plan.source_path,
                new_full_path=plan.new_full_path,
                success=True,
                message=f"생성 완료: {dst.name}",
            ))
        except OSError as e:
            results.append(GenerationResult(
                source_path=plan.source_path,
                new_full_path=plan.new_full_path,
                success=False,
                message=f"파일 생성 실패: {e}",
            ))

    return results
