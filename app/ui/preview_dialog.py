"""
생성 미리보기 팝업 다이얼로그.
생성될 파일명 목록을 보여주고 확인/취소를 받습니다.
"""

from typing import List

import customtkinter as ctk

from app.core.file_generator import GenerationPlan


class PreviewDialog(ctk.CTkToplevel):
    def __init__(self, master, plans: List[GenerationPlan]):
        super().__init__(master)
        self.title("생성 미리보기")
        self.geometry("620x440")
        self.resizable(False, False)
        self.grab_set()  # 모달 동작

        self._plans = plans
        self._confirmed = False

        self._build_ui()
        self._populate()
        self._center_on_parent(master)

    # ── UI 구성 ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # 상단 안내
        info = ctk.CTkLabel(
            self,
            text="아래 파일들이 생성됩니다. 확인 후 [생성] 버튼을 누르세요.",
            font=ctk.CTkFont(family="맑은 고딕", size=12),
            anchor="w",
        )
        info.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))

        # 목록 스크롤
        self._scroll = ctk.CTkScrollableFrame(self, label_text="")
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        self._scroll.columnconfigure(0, weight=1)
        self._scroll.columnconfigure(1, weight=0)
        self._scroll.columnconfigure(2, weight=1)

        # 헤더 행
        for col, text in enumerate(["원본 파일명", "→", "새 파일명"]):
            lbl = ctk.CTkLabel(
                self._scroll,
                text=text,
                font=ctk.CTkFont(family="맑은 고딕", size=11, weight="bold"),
                anchor="w" if col != 1 else "center",
            )
            lbl.grid(row=0, column=col, sticky="ew", padx=6, pady=(0, 4))

        # 하단 버튼
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=10)
        btn_frame.columnconfigure(0, weight=1)

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="취소",
            width=100,
            fg_color="gray50",
            hover_color="gray40",
            command=self._cancel,
        )
        cancel_btn.grid(row=0, column=1, padx=(0, 8))

        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="생성  ▶",
            width=120,
            fg_color="#2d6a4f",
            hover_color="#1b4332",
            command=self._confirm,
        )
        confirm_btn.grid(row=0, column=2)

    def _populate(self):
        for i, plan in enumerate(self._plans):
            row = i + 1  # 헤더가 0행

            from pathlib import Path
            src_name = Path(plan.source_path).name
            new_name = plan.new_filename

            # 원본
            src_lbl = ctk.CTkLabel(
                self._scroll, text=src_name, anchor="w",
                font=ctk.CTkFont(family="맑은 고딕", size=11),
                wraplength=200,
            )
            src_lbl.grid(row=row, column=0, sticky="ew", padx=6, pady=2)

            # 화살표
            arrow = ctk.CTkLabel(self._scroll, text="→", anchor="center")
            arrow.grid(row=row, column=1, padx=4)

            # 새 이름 (이미 존재하면 경고 색)
            text_color = ("#cc0000", "#ff6b6b") if plan.already_exists else ("gray10", "gray90")
            suffix = "  ⚠ 이미 존재" if plan.already_exists else ""
            new_lbl = ctk.CTkLabel(
                self._scroll,
                text=new_name + suffix,
                anchor="w",
                font=ctk.CTkFont(family="맑은 고딕", size=11),
                text_color=text_color,
                wraplength=220,
            )
            new_lbl.grid(row=row, column=2, sticky="ew", padx=6, pady=2)

    # ── 동작 메서드 ──────────────────────────────────────────────────────────
    def _confirm(self):
        self._confirmed = True
        self.destroy()

    def _cancel(self):
        self._confirmed = False
        self.destroy()

    def is_confirmed(self) -> bool:
        return self._confirmed

    def _center_on_parent(self, parent):
        parent.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{px - 310}+{py - 220}")
