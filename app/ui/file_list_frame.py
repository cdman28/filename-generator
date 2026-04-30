"""
파일 목록 패널.
선택된 폴더의 파일들을 표시하고, 패턴 감지 결과 및 체크박스를 제공합니다.
"""

import os
import tkinter as tk
from datetime import date
from pathlib import Path
from typing import Callable, List, Dict

import customtkinter as ctk

from app.core.pattern_detector import scan_folder, FilePatternInfo, detect_pattern_in_name
from app.core.date_calculator import suggest_next_date, parse_date_from_text, infer_next_date


CYCLE_KR = {"weekly": "주 단위", "monthly": "월 단위"}
PATTERN_COLOR = {
    "weekly":  ("#1d6aab", "#4da6ff"),
    "monthly": ("#6a1d6a", "#d28cff"),
    "none":    ("#888888", "#888888"),
}
FONT_FAMILY = "맑은 고딕"
MAX_DISPLAY = 10  # 기본 표시 파일 수


class FileListFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", ("white", "#2b2b2b"))
        super().__init__(master, **kwargs)
        self._folder_path: str = ""
        self._all_file_infos: List[FilePatternInfo] = []  # 전체 파일 목록
        self._file_infos: List[FilePatternInfo] = []      # 현재 표시 중인 목록
        self._display_limit: int = MAX_DISPLAY            # 현재 표시 한도
        self._check_vars: Dict[str, tk.BooleanVar] = {}  # filename → BooleanVar

        self._build_ui()

    # ── UI 구성 ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # 상단 툴바 (폴더 경로 + 전체선택)
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        toolbar.columnconfigure(0, weight=1)

        self._path_label = ctk.CTkLabel(
            toolbar,
            text="← 왼쪽에서 폴더를 선택하세요",
            anchor="w",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=("gray50", "gray60"),
        )
        self._path_label.grid(row=0, column=0, sticky="ew")

        self._select_all_var = tk.BooleanVar(value=False)
        self._select_all_cb = ctk.CTkCheckBox(
            toolbar,
            text="전체 선택",
            variable=self._select_all_var,
            command=self._toggle_all,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
        )
        self._select_all_cb.grid(row=0, column=1, padx=(8, 0))

        # 파일 목록 (스크롤)
        self._scroll = ctk.CTkScrollableFrame(self, label_text="", fg_color=("white", "#2b2b2b"))
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        self._scroll.columnconfigure(0, weight=1)  # 체크박스+파일명
        self._scroll.columnconfigure(1, weight=0)  # 패턴 태그

        # 빈 상태 안내 레이블
        self._empty_label = ctk.CTkLabel(
            self._scroll,
            text="폴더를 선택하면 파일 목록이 표시됩니다.",
            text_color=("gray50", "gray60"),
        )
        self._empty_label.grid(row=0, column=0, columnspan=2, pady=40)

    # ── 공개 메서드 ───────────────────────────────────────────────────────────
    def load_folder(self, folder_path: str):
        """폴더를 스캔하여 파일 목록을 갱신합니다. 기본 10개만 표시합니다."""
        self._folder_path = folder_path
        self._all_file_infos = scan_folder(folder_path)
        self._display_limit = MAX_DISPLAY
        self._file_infos = self._all_file_infos[:self._display_limit]
        self._check_vars.clear()
        self._select_all_var.set(False)
        self._refresh_list()
        self._path_label.configure(text=folder_path)

    def get_selected_files(self) -> List[str]:
        """체크된 파일들의 전체 경로 목록을 반환합니다."""
        selected = []
        for fi in self._file_infos:
            var = self._check_vars.get(fi.filename)
            if var and var.get():
                selected.append(str(Path(self._folder_path) / fi.filename))
        return selected

    def get_suggested_date(self) -> date | None:
        """
        폴더 내 파일들의 날짜 목록을 분석하여 다음 순서의 날짜를 수준합니다.
        1) 체크된 파일이 있으면 해당 파일들의 패턴명과 같은 모든 파일의 날짜를 분석합니다.
        2) 체크된 파일이 없으면 폴더 내 전체 파일의 날짜를 분석합니다.
        """
        # 체크된 파일들의 패턴 이름 수집
        checked_pattern_names: set = set()
        for fi in self._file_infos:
            var = self._check_vars.get(fi.filename)
            if var and var.get() and fi.pattern:
                checked_pattern_names.add(fi.pattern.pattern_name)

        # 분석 대상 파일 필터링
        if checked_pattern_names:
            targets = [
                fi for fi in self._all_file_infos
                if fi.pattern and fi.pattern.pattern_name in checked_pattern_names
            ]
        else:
            targets = [fi for fi in self._all_file_infos if fi.pattern]

        if not targets:
            return None

        dates = []
        for fi in targets:
            d = parse_date_from_text(fi.pattern.pattern_name, fi.pattern.matched_text)
            if d:
                dates.append(d)

        return infer_next_date(dates)

    def get_dominant_cycle(self) -> str | None:
        """체크된 파일들 중 가장 많이 나타나는 주기를 반환합니다."""
        counts: Dict[str, int] = {}
        for fi in self._file_infos:
            var = self._check_vars.get(fi.filename)
            if var and var.get() and fi.pattern:
                c = fi.pattern.cycle
                counts[c] = counts.get(c, 0) + 1
        if not counts:
            return None
        return max(counts, key=lambda k: counts[k])

    # ── 내부 메서드 ──────────────────────────────────────────────────────────
    def _refresh_list(self):
        for widget in self._scroll.winfo_children():
            widget.destroy()

        if not self._all_file_infos:
            lbl = ctk.CTkLabel(
                self._scroll,
                text="폴더에 파일이 없습니다.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=("gray50", "gray60"),
            )
            lbl.grid(row=0, column=0, columnspan=2, pady=40)
            return

        self._file_infos = self._all_file_infos[:self._display_limit]
        for i, fi in enumerate(self._file_infos):
            self._add_file_row(i, fi)

        # 더 불러오기 버튼 (표시 중인 수 < 전체 수 일 때)
        remaining = len(self._all_file_infos) - len(self._file_infos)
        if remaining > 0:
            load_more_btn = ctk.CTkButton(
                self._scroll,
                text=f"더 불러오기  ({remaining}개 더 있음)",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                text_color=("#1d6aab", "#4da6ff"),
                command=self._load_more,
            )
            load_more_btn.grid(
                row=len(self._file_infos), column=0, columnspan=2,
                sticky="ew", padx=8, pady=(4, 2),
            )
        else:
            total = len(self._all_file_infos)
            summary = ctk.CTkLabel(
                self._scroll,
                text=f"전체 {total}개 파일 표시 중",
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=("gray60", "gray50"),
            )
            summary.grid(
                row=len(self._file_infos), column=0, columnspan=2,
                sticky="w", padx=12, pady=(4, 2),
            )

    def _load_more(self):
        """표시 한도를 10 늘려 추가 파일을 불러옵니다."""
        self._display_limit += MAX_DISPLAY
        self._refresh_list()

    def _add_file_row(self, row_idx: int, fi: FilePatternInfo):
        var = tk.BooleanVar(value=False)
        self._check_vars[fi.filename] = var

        # 체크박스 + 파일명
        cb = ctk.CTkCheckBox(
            self._scroll,
            text=fi.filename,
            variable=var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self._update_select_all_state,
        )
        cb.grid(row=row_idx, column=0, sticky="w", padx=(4, 8), pady=3)

        # 패턴 태그
        if fi.pattern:
            cycle_key = fi.pattern.cycle
            tag_text = f"{CYCLE_KR.get(cycle_key, cycle_key)}  [{fi.pattern.pattern_name}]"
            fg, text_c = PATTERN_COLOR.get(cycle_key, PATTERN_COLOR["none"])
            tag = ctk.CTkLabel(
                self._scroll,
                text=tag_text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                fg_color=(fg, fg),
                text_color="white",
                corner_radius=4,
                padx=6,
                pady=2,
            )
        else:
            tag = ctk.CTkLabel(
                self._scroll,
                text="패턴 미감지",
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                fg_color=PATTERN_COLOR["none"][0],
                text_color="white",
                corner_radius=4,
                padx=6,
                pady=2,
            )
        tag.grid(row=row_idx, column=1, sticky="e", padx=(0, 4), pady=3)

    def _toggle_all(self):
        state = self._select_all_var.get()
        for var in self._check_vars.values():
            var.set(state)

    def _update_select_all_state(self):
        all_checked = all(v.get() for v in self._check_vars.values()) if self._check_vars else False
        self._select_all_var.set(all_checked)
