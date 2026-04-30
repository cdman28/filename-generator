"""
생성 결과 다이얼로그.
성공/실패 결과를 표시하고, 성공한 파일은 바로 열 수 있는 버튼을 제공합니다.
"""

import os
from pathlib import Path
from typing import List

import customtkinter as ctk

from app.core.file_generator import GenerationResult

FONT = "맑은 고딕"


class ResultDialog(ctk.CTkToplevel):
    def __init__(self, master, results: List[GenerationResult]):
        super().__init__(master)
        self.title("생성 결과")
        self.geometry("600x420")
        self.resizable(False, False)
        self.grab_set()

        self._results = results
        self._build_ui()
        self._populate()
        self._center_on_parent(master)

    # ── UI 구성 ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # 요약 헤더
        succeeded = sum(1 for r in self._results if r.success)
        failed = sum(1 for r in self._results if not r.success)
        summary_parts = []
        if succeeded:
            summary_parts.append(f"✅ 생성 완료: {succeeded}개")
        if failed:
            summary_parts.append(f"❌ 실패: {failed}개")

        summary_lbl = ctk.CTkLabel(
            self,
            text="   ".join(summary_parts),
            font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
            anchor="w",
        )
        summary_lbl.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))

        # 결과 목록
        self._scroll = ctk.CTkScrollableFrame(self, label_text="")
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        self._scroll.columnconfigure(0, weight=1)

        # 닫기 버튼
        close_btn = ctk.CTkButton(
            self,
            text="닫기",
            width=100,
            height=34,
            font=ctk.CTkFont(family=FONT, size=12),
            fg_color="gray50",
            hover_color="gray40",
            command=self.destroy,
        )
        close_btn.grid(row=2, column=0, sticky="e", padx=16, pady=10)

    def _populate(self):
        for i, result in enumerate(self._results):
            self._add_result_row(i, result)

    def _add_result_row(self, row_idx: int, result: GenerationResult):
        row_frame = ctk.CTkFrame(
            self._scroll,
            fg_color=("gray95", "#1e1e1e") if result.success else ("#fff0f0", "#3a1a1a"),
            corner_radius=6,
        )
        row_frame.grid(row=row_idx, column=0, sticky="ew", padx=2, pady=3)
        row_frame.columnconfigure(0, weight=1)

        if result.success:
            new_name = Path(result.new_full_path).name
            icon = "✅"
            text = new_name
            text_color = ("gray10", "gray90")
        else:
            icon = "❌"
            text = result.message
            text_color = ("#cc0000", "#ff6b6b")

        lbl = ctk.CTkLabel(
            row_frame,
            text=f"  {icon}  {text}",
            anchor="w",
            font=ctk.CTkFont(family=FONT, size=11),
            text_color=text_color,
            wraplength=430,
        )
        lbl.grid(row=0, column=0, sticky="ew", padx=8, pady=6)

        # 성공한 파일에만 "열기" 버튼 표시
        if result.success and Path(result.new_full_path).exists():
            open_btn = ctk.CTkButton(
                row_frame,
                text="열기",
                width=56,
                height=26,
                font=ctk.CTkFont(family=FONT, size=11),
                fg_color=("#1d6aab", "#1a5a99"),
                hover_color=("#155588", "#124a7d"),
                command=lambda p=result.new_full_path: self._open_file(p),
            )
            open_btn.grid(row=0, column=1, padx=(4, 8), pady=4)

    def _open_file(self, path: str):
        try:
            os.startfile(path)
        except OSError as e:
            from tkinter import messagebox
            messagebox.showerror("열기 실패", f"파일을 열 수 없습니다:\n{e}", parent=self)

    def _center_on_parent(self, parent):
        parent.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{px - 300}+{py - 210}")
