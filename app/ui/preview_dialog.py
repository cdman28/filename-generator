"""
생성 미리보기 팝업 다이얼로그.
생성될 파일명 목록을 보여주고 확인/취소를 받습니다.
checkable=True 로 열면 각 행에 체크박스가 표시되어 제외 선택 가능.
"""

import tkinter as tk
from pathlib import Path
from typing import List

import customtkinter as ctk

from app.core.file_generator import GenerationPlan


class PreviewDialog(ctk.CTkToplevel):
    def __init__(self, master, plans: List[GenerationPlan], checkable: bool = False):
        super().__init__(master)
        self.title("생성 미리보기")
        self.geometry("660x480")
        self.resizable(False, False)
        self.grab_set()  # 모달 동작

        self._plans = plans
        self._checkable = checkable
        self._confirmed = False
        self._check_vars: List[tk.BooleanVar] = []

        self._build_ui()
        self._populate()
        self._center_on_parent(master)

    # ── UI 구성 ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # 상단 안내
        if self._checkable:
            guide = "체크한 파일만 생성됩니다. 제외하려면 체크를 해제하세요."
        else:
            guide = "아래 파일들이 생성됩니다. 확인 후 [생성] 버튼을 누르세요."

        ctk.CTkLabel(
            self,
            text=guide,
            font=ctk.CTkFont(family="맑은 고딕", size=12),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))

        # 목록 스크롤
        self._scroll = ctk.CTkScrollableFrame(self, label_text="")
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)

        # 컬럼 구성: checkable이면 체크박스 컬럼 추가
        if self._checkable:
            self._scroll.columnconfigure(0, weight=0)  # 체크박스
            self._scroll.columnconfigure(1, weight=1)  # 원본
            self._scroll.columnconfigure(2, weight=0)  # 화살표
            self._scroll.columnconfigure(3, weight=1)  # 새 이름
        else:
            self._scroll.columnconfigure(0, weight=1)
            self._scroll.columnconfigure(1, weight=0)
            self._scroll.columnconfigure(2, weight=1)

        # 헤더 행
        col_offset = 1 if self._checkable else 0
        if self._checkable:
            # 전체 선택/해제 체크박스
            self._all_var = tk.BooleanVar(value=True)
            all_chk = ctk.CTkCheckBox(
                self._scroll,
                text="",
                variable=self._all_var,
                width=22,
                command=self._toggle_all,
            )
            all_chk.grid(row=0, column=0, padx=(4, 0), pady=(0, 4))

        for col, text in enumerate(["원본 파일명", "→", "새 파일명"]):
            ctk.CTkLabel(
                self._scroll,
                text=text,
                font=ctk.CTkFont(family="맑은 고딕", size=11, weight="bold"),
                anchor="w" if col != 1 else "center",
            ).grid(row=0, column=col + col_offset, sticky="ew", padx=6, pady=(0, 4))

        # 하단 버튼
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=10)
        btn_frame.columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_frame,
            text="취소",
            width=100,
            fg_color="gray50",
            hover_color="gray40",
            command=self._cancel,
        ).grid(row=0, column=1, padx=(0, 8))

        ctk.CTkButton(
            btn_frame,
            text="생성  ▶",
            width=120,
            fg_color="#2d6a4f",
            hover_color="#1b4332",
            command=self._confirm,
        ).grid(row=0, column=2)

    def _populate(self):
        col_offset = 1 if self._checkable else 0

        for i, plan in enumerate(self._plans):
            row = i + 1  # 헤더가 0행

            src_name = Path(plan.source_path).name
            new_name = plan.new_filename

            if self._checkable:
                var = tk.BooleanVar(value=True)
                self._check_vars.append(var)
                chk = ctk.CTkCheckBox(
                    self._scroll,
                    text="",
                    variable=var,
                    width=22,
                    command=self._update_all_checkbox,
                )
                chk.grid(row=row, column=0, padx=(4, 0), pady=2)

            # 원본
            ctk.CTkLabel(
                self._scroll,
                text=src_name,
                anchor="w",
                font=ctk.CTkFont(family="맑은 고딕", size=11),
                wraplength=200,
            ).grid(row=row, column=0 + col_offset, sticky="ew", padx=6, pady=2)

            # 화살표
            ctk.CTkLabel(
                self._scroll, text="→", anchor="center"
            ).grid(row=row, column=1 + col_offset, padx=4)

            # 새 이름 (이미 존재하면 경고 색)
            text_color = ("#cc0000", "#ff6b6b") if plan.already_exists else ("gray10", "gray90")
            suffix = "  ⚠ 이미 존재" if plan.already_exists else ""
            ctk.CTkLabel(
                self._scroll,
                text=new_name + suffix,
                anchor="w",
                font=ctk.CTkFont(family="맑은 고딕", size=11),
                text_color=text_color,
                wraplength=220,
            ).grid(row=row, column=2 + col_offset, sticky="ew", padx=6, pady=2)

    # ── 전체 선택/해제 ────────────────────────────────────────────────────────
    def _toggle_all(self):
        val = self._all_var.get()
        for v in self._check_vars:
            v.set(val)

    def _update_all_checkbox(self):
        if not self._check_vars:
            return
        all_checked = all(v.get() for v in self._check_vars)
        any_checked = any(v.get() for v in self._check_vars)
        if all_checked:
            self._all_var.set(True)
        elif any_checked:
            # 부분 선택: 일단 True 유지 (다음 클릭 시 전체 해제 직관적)
            self._all_var.set(True)
        else:
            self._all_var.set(False)

    # ── 동작 메서드 ──────────────────────────────────────────────────────────
    def _confirm(self):
        self._confirmed = True
        self.destroy()

    def _cancel(self):
        self._confirmed = False
        self.destroy()

    def is_confirmed(self) -> bool:
        return self._confirmed

    def get_checked_plans(self) -> List[GenerationPlan]:
        """체크박스 모드에서 체크된 plan만 반환합니다."""
        if not self._checkable or not self._check_vars:
            return self._plans
        return [p for p, v in zip(self._plans, self._check_vars) if v.get()]

    def _center_on_parent(self, parent):
        parent.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{px - 330}+{py - 240}")