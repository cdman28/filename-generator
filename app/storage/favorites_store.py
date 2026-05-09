"""
즐겨찾기 폴더 목록을 JSON 파일로 저장하고 로드합니다.
자동 저장 위치: %TEMP%\\파일명수정도우미\\favorites.json
"""

import json
import os
import tempfile
from pathlib import Path
from typing import List, Dict

# 윈도우 시스템 임시폴더 내 앱 전용 서브폴더
DATA_DIR = Path(tempfile.gettempdir()) / "파일명수정도우미"
FAVORITES_FILE = DATA_DIR / "favorites.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def detect_folder_group(folder_path: str) -> str:
    """폴더 내 파일 패턴을 분석하여 그룹(weekly/monthly/unknown)을 자동 감지합니다."""
    try:
        from app.core.pattern_detector import scan_folder
        files = scan_folder(folder_path)
        if not files:
            return "unknown"
        cycles = [f.cycle for f in files if f.cycle]
        if not cycles:
            return "unknown"
        weekly_count = cycles.count("weekly")
        monthly_count = cycles.count("monthly")
        if weekly_count == 0 and monthly_count == 0:
            return "unknown"
        return "weekly" if weekly_count >= monthly_count else "monthly"
    except Exception:
        return "unknown"


def load_favorites() -> List[Dict]:
    """즐겨찾기 목록을 로드합니다. 파일이 없으면 빈 목록을 반환합니다."""
    _ensure_data_dir()
    if not FAVORITES_FILE.exists():
        return []
    with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 존재하지 않는 폴더는 제거
    result = [item for item in data if os.path.isdir(item.get("path", ""))]
    # group 필드 기본값 보완 (구버전 데이터 호환)
    for item in result:
        if "group" not in item:
            item["group"] = "unknown"
    return result


def save_favorites(favorites: List[Dict]) -> None:
    """즐겨찾기 목록을 저장합니다."""
    _ensure_data_dir()
    with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
        json.dump(favorites, f, ensure_ascii=False, indent=2)


def add_favorite(folder_path: str, display_name: str = "") -> List[Dict]:
    """즐겨찾기에 폴더를 추가합니다. 중복 경로는 무시합니다."""
    favorites = load_favorites()
    normalized = os.path.normpath(folder_path)
    # 중복 체크
    for item in favorites:
        if os.path.normpath(item["path"]) == normalized:
            return favorites
    name = display_name.strip() or os.path.basename(normalized)
    group = detect_folder_group(normalized)
    favorites.append({"path": normalized, "name": name, "group": group})
    save_favorites(favorites)
    return favorites


def reorder_favorites(new_order_paths: List[str]) -> List[Dict]:
    """경로 목록 순서에 따라 즐겨찾기를 재정렬합니다."""
    favorites = load_favorites()
    path_map = {os.path.normpath(f["path"]): f for f in favorites}
    reordered = []
    seen: set = set()
    for p in new_order_paths:
        norm = os.path.normpath(p)
        if norm in path_map and norm not in seen:
            reordered.append(path_map[norm])
            seen.add(norm)
    # 순서 목록에 없는 항목은 뒤에 유지
    for f in favorites:
        norm = os.path.normpath(f["path"])
        if norm not in seen:
            reordered.append(f)
    save_favorites(reordered)
    return reordered


def remove_favorite(folder_path: str) -> List[Dict]:
    """즐겨찾기에서 폴더를 제거합니다."""
    favorites = load_favorites()
    normalized = os.path.normpath(folder_path)
    favorites = [f for f in favorites if os.path.normpath(f["path"]) != normalized]
    save_favorites(favorites)
    return favorites


def rename_favorite(folder_path: str, new_name: str) -> List[Dict]:
    """즐겨찾기 표시 이름을 변경합니다."""
    favorites = load_favorites()
    normalized = os.path.normpath(folder_path)
    for item in favorites:
        if os.path.normpath(item["path"]) == normalized:
            item["name"] = new_name.strip()
            break
    save_favorites(favorites)
    return favorites


def export_favorites(target_path: str) -> None:
    """현재 즐겨찾기 목록을 사용자가 지정한 경로에 저장(내보내기)합니다."""
    favorites = load_favorites()
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(favorites, f, ensure_ascii=False, indent=2)


def import_favorites(source_path: str) -> List[Dict]:
    """외부 JSON 파일에서 즐겨찾기를 불러와 현재 목록과 병합합니다. 중복 경로는 무시합니다."""
    with open(source_path, "r", encoding="utf-8") as f:
        imported = json.load(f)
    current = load_favorites()
    existing_paths = {os.path.normpath(f["path"]) for f in current}
    for item in imported:
        normalized = os.path.normpath(item.get("path", ""))
        if normalized and normalized not in existing_paths and os.path.isdir(normalized):
            current.append({
                "path": normalized,
                "name": item.get("name", os.path.basename(normalized)),
                "group": item.get("group", "unknown"),
            })
            existing_paths.add(normalized)
    save_favorites(current)
    return current
