"""
메인 윈도우 레이아웃.
사이드바(좌), 파일목록(중), 하단 날짜+생성 버튼으로 구성됩니다.
"""

import json
import os
import tkinter as tk
from datetime import date, timedelta
from pathlib import Path
from tkinter import messagebox
from typing import List

import customtkinter as ctk

from app.ui.sidebar import SidebarFrame
from app.ui.file_list_frame import FileListFrame
from app.ui.preview_dialog import PreviewDialog
from app.ui.result_dialog import ResultDialog
from app.core.file_generator import build_plans_for_folder, build_plan, execute_plans
from app.core.date_calculator import suggest_next_date, infer_next_date, parse_date_from_text
from app.core.pattern_detector import scan_folder
from app.version import VERSION, APP_NAME


LOG_FILE = Path(__file__).parent.parent.parent / "data" / "history.json"


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("960x620")
        self.minsize(800, 500)

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("green")

        self._build_ui()

    # ── UI 구성 ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 좌측: 즐겨찾기 사이드바
        self._sidebar = SidebarFrame(
            self,
            on_folder_selected=self._on_folder_selected,
            on_batch_generate=self._batch_generate,
            width=220,
        )
        self._sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(8, 0), pady=8)

        # 중앙: 파일 목록
        self._file_list = FileListFrame(self)
        self._file_list.grid(row=0, column=1, sticky="nsew", padx=8, pady=(8, 0))

        # 하단: 날짜 + 버튼 바
        self._build_bottom_bar()

    def _build_bottom_bar(self):
        bar = ctk.CTkFrame(self, height=60)
        bar.grid(row=1, column=1, sticky="ew", padx=8, pady=8)
        bar.columnconfigure(1, weight=1)

        # 날짜 레이블
        date_lbl = ctk.CTkLabel(
            bar, text="생성 날짜:",
            font=ctk.CTkFont(family="맑은 고딕", size=13),
        )
        date_lbl.grid(row=0, column=0, padx=(12, 6), pady=12)

        # 날짜 입력 (YYYY-MM-DD 텍스트 입력)
        self._date_entry = ctk.CTkEntry(
            bar,
            placeholder_text="YYYY-MM-DD",
            width=130,
            font=ctk.CTkFont(family="맑은 고딕", size=13),
        )
        self._date_entry.grid(row=0, column=1, sticky="w", padx=(0, 6))

        # 자동 계산 버튼
        auto_btn = ctk.CTkButton(
            bar,
            text="자동 계산",
            width=90,
            height=32,
            command=self._auto_fill_date,
            font=ctk.CTkFont(family="맑은 고딕", size=12),
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            text_color=("gray10", "gray90"),
        )
        auto_btn.grid(row=0, column=2, padx=(0, 12))

        # 미리보기 버튼
        preview_btn = ctk.CTkButton(
            bar,
            text="미리보기",
            width=100,
            height=36,
            command=self._show_preview,
            font=ctk.CTkFont(family="맑은 고딕", size=12),
            fg_color=("#1d6aab", "#1a5a99"),
            hover_color=("#155588", "#124a7d"),
        )
        preview_btn.grid(row=0, column=3, padx=(0, 8))

        # 생성 버튼
        generate_btn = ctk.CTkButton(
            bar,
            text="생성  ▶",
            width=110,
            height=36,
            command=self._generate,
            font=ctk.CTkFont(family="맑은 고딕", size=12),
            fg_color="#2d6a4f",
            hover_color="#1b4332",
        )
        generate_btn.grid(row=0, column=4, padx=(0, 12))

    # ── 이벤트 핸들러 ─────────────────────────────────────────────────────────
    def _on_folder_selected(self, folder_path: str):
        self._file_list.load_folder(folder_path)
        # 폴더 선택 시 자동으로 날짜 계산
        self._auto_fill_date()

    def _auto_fill_date(self):
        """체크된 파일의 패턴을 기반으로 날짜를 자동 계산해 입력란에 채웁니다."""
        suggested = self._file_list.get_suggested_date()
        if suggested is None:
            # 체크된 파일이 없거나 패턴 미감지 → 오늘 기준 주 단위 제안
            cycle = self._file_list.get_dominant_cycle() or "weekly"
            suggested = suggest_next_date(cycle)

        self._date_entry.delete(0, tk.END)
        self._date_entry.insert(0, suggested.strftime("%Y-%m-%d"))

    def _parse_date_input(self) -> date | None:
        raw = self._date_entry.get().strip()
        try:
            return date.fromisoformat(raw)
        except ValueError:
            messagebox.showerror("날짜 오류", f"날짜 형식이 올바르지 않습니다.\n예: 2026-05-10\n입력값: {raw}")
            return None

    def _show_preview(self):
        selected = self._file_list.get_selected_files()
        if not selected:
            messagebox.showwarning("선택 없음", "생성할 파일을 하나 이상 체크해주세요.")
            return
        target_date = self._parse_date_input()
        if target_date is None:
            return
        plans = build_plans_for_folder(selected, target_date)
        if not plans:
            messagebox.showwarning("패턴 없음", "선택한 파일에서 날짜 패턴을 감지하지 못했습니다.\n파일명에 날짜가 포함되어 있는지 확인해주세요.")
            return
        dlg = PreviewDialog(self, plans)
        self.wait_window(dlg)

    def _generate(self):
        selected = self._file_list.get_selected_files()
        if not selected:
            messagebox.showwarning("선택 없음", "생성할 파일을 하나 이상 체크해주세요.")
            return
        target_date = self._parse_date_input()
        if target_date is None:
            return

        plans = build_plans_for_folder(selected, target_date)
        if not plans:
            messagebox.showwarning("패턴 없음", "선택한 파일에서 날짜 패턴을 감지하지 못했습니다.")
            return

        # 미리보기 팝업을 통해 최종 확인
        dlg = PreviewDialog(self, plans)
        self.wait_window(dlg)
        if not dlg.is_confirmed():
            return

        # 이미 존재하는 파일이 있으면 덮어쓰기 여부 확인
        has_existing = any(p.already_exists for p in plans)
        overwrite = False
        if has_existing:
            overwrite = messagebox.askyesno(
                "파일 중복",
                "이미 존재하는 파일이 있습니다.\n덮어쓰시겠습니까?",
            )

        results = execute_plans(plans, overwrite=overwrite)
        self._save_history(results)

        # 결과 다이얼로그 (파일 열기 버튼 포함)
        dlg = ResultDialog(self, results)
        self.wait_window(dlg)

        # 파일 목록 새로고침
        folder = self._file_list._folder_path
        if folder:
            self._file_list.load_folder(folder)

    # ── 그룹 일괄 생성 ─────────────────────────────────────────────────────────
    def _batch_generate(self, group_key: str, folder_paths: List[str]):
        """주간 또는 월간 그룹의 모든 폴더를 날짜 자동 추론 후 일괄 생성합니다."""
        from app.core.file_generator import GenerationPlan

        all_plans: List[GenerationPlan] = []
        skipped: List[str] = []

        for folder_path in folder_paths:
            file_infos = scan_folder(folder_path)
            # FilePatternInfo.pattern 이 DetectedPattern (cycle, pattern_name, matched_text)
            detected = [fi for fi in file_infos if fi.pattern]
            if not detected:
                skipped.append(folder_path)
                continue

            # 날짜 부분(matched_text)을 파일명에서 제거한 값을 키로 그룹핑
            # scan_folder는 mtime 내림차순 → 첫 번째가 각 그룹의 가장 최신 파일
            seen: dict = {}
            for fi in detected:
                key = fi.filename.replace(fi.pattern.matched_text, "", 1)
                if key not in seen:
                    seen[key] = fi
            representative_files = list(seen.values())

            # 대표 파일(패턴별 최신 1개)에서만 날짜 추출 → 다음 날짜 추론
            dates = []
            for fi in representative_files:
                d = parse_date_from_text(fi.pattern.pattern_name, fi.pattern.matched_text)
                if d:
                    dates.append(d)

            target_date = infer_next_date(dates)
            if target_date is None:
                skipped.append(folder_path)
                continue

            # 대표 파일(패턴별 최신 1개)로만 plan 생성
            for fi in representative_files:
                full_path = os.path.join(folder_path, fi.filename)
                plan = build_plan(full_path, target_date)
                if plan:
                    all_plans.append(plan)

        if not all_plans:
            msg = "생성할 파일을 찾지 못했습니다.\n폴더 내 날짜 패턴이 있는 파일을 확인해주세요."
            if skipped:
                msg += "\n\n건너뜀: " + "\n".join(os.path.basename(p) for p in skipped)
            messagebox.showwarning("일괄 생성", msg)
            return

        # checkable=True: 각 파일 행에 체크박스 표시 → 제외 선택 가능
        dlg = PreviewDialog(self, all_plans, checkable=True)
        self.wait_window(dlg)
        if not dlg.is_confirmed():
            return

        # 체크된 plan만 실행
        final_plans = dlg.get_checked_plans()
        if not final_plans:
            messagebox.showinfo("일괄 생성", "선택된 파일이 없습니다.")
            return

        has_existing = any(p.already_exists for p in final_plans)
        overwrite = False
        if has_existing:
            overwrite = messagebox.askyesno(
                "파일 중복", "이미 존재하는 파일이 있습니다.\n덮어쓰시겠습니까?"
            )

        results = execute_plans(final_plans, overwrite=overwrite)
        self._save_history(results)

        dlg = ResultDialog(self, results)
        self.wait_window(dlg)

    # ── 이력 저장 ─────────────────────────────────────────────────────────────
    def _save_history(self, results):
        from app.core.file_generator import GenerationResult
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        history = []
        if LOG_FILE.exists():
            try:
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except (json.JSONDecodeError, OSError):
                history = []

        now = date.today().isoformat()
        for r in results:
            history.append({
                "date": now,
                "source": r.source_path,
                "new": r.new_full_path,
                "success": r.success,
                "message": r.message,
            })

        # 최근 500건만 유지
        history = history[-500:]
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
