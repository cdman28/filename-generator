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


def load_favorites() -> List[Dict]:
    """즐겨찾기 목록을 로드합니다. 파일이 없으면 빈 목록을 반환합니다."""
    _ensure_data_dir()
    if not FAVORITES_FILE.exists():
        return []
    with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 존재하지 않는 폴더는 제거
    return [item for item in data if os.path.isdir(item.get("path", ""))]


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
    favorites.append({"path": normalized, "name": name})
    save_favorites(favorites)
    return favorites


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
            current.append({"path": normalized, "name": item.get("name", os.path.basename(normalized))})
            existing_paths.add(normalized)
    save_favorites(current)
    return current
