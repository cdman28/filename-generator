"""
즐겨찾기 사이드바 패널.
폴더 목록 표시, 추가/삭제/이름변경 기능 제공.
"""

import os
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from typing import Callable, List, Dict

import customtkinter as ctk

from app.storage import favorites_store
from app.storage.favorites_store import export_favorites, import_favorites


class SidebarFrame(ctk.CTkFrame):
    def __init__(self, master, on_folder_selected: Callable[[str], None], **kwargs):
        kwargs.setdefault("fg_color", ("white", "#2b2b2b"))
        super().__init__(master, **kwargs)
        self._on_folder_selected = on_folder_selected
        self._selected_path: str = ""
        self._buttons: List[ctk.CTkButton] = []

        self._build_ui()
        self._load()

    # ── UI 구성 ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        # 헤더
        header = ctk.CTkLabel(
            self, text="📁  즐겨찾기 폴더",
            font=ctk.CTkFont(family="맑은 고딕", size=13, weight="bold"),
            anchor="w",
        )
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        # 스크롤 가능한 폴더 목록 영역
        self._scroll = ctk.CTkScrollableFrame(self, label_text="", fg_color=("white", "#2b2b2b"))
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)
        self._scroll.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # 폴더 추가 버튼
        add_btn = ctk.CTkButton(
            self, text="＋  폴더 추가",
            command=self._add_folder,
            height=34,
            font=ctk.CTkFont(family="맑은 고딕", size=12),
            fg_color="#2d6a4f",
            hover_color="#1b4332",
        )
        add_btn.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 2))

        # 하단 버튼 형 (저장 / 불러오기)
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 10))
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)

        save_btn = ctk.CTkButton(
            btn_row, text="파일로 저장",
            command=self._save_to_file,
            height=30,
            font=ctk.CTkFont(family="맑은 고딕", size=11),
            fg_color=("#1d6aab", "#1a5a99"),
            hover_color=("#155588", "#124a7d"),
        )
        save_btn.grid(row=0, column=0, sticky="ew", padx=(0, 2))

        load_btn = ctk.CTkButton(
            btn_row, text="불러오기",
            command=self._load_from_file,
            height=30,
            font=ctk.CTkFont(family="맑은 고딕", size=11),
            fg_color=("gray60", "gray40"),
            hover_color=("gray50", "gray30"),
        )
        load_btn.grid(row=0, column=1, sticky="ew", padx=(2, 0))

    # ── 내부 메서드 ──────────────────────────────────────────────────────────
    def _load(self):
        """즐겨찾기 목록을 다시 로드하여 UI를 갱신합니다."""
        for widget in self._scroll.winfo_children():
            widget.destroy()
        self._buttons.clear()

        favorites = favorites_store.load_favorites()
        for i, item in enumerate(favorites):
            self._add_row(i, item)

    def _add_row(self, row_idx: int, item: Dict):
        path = item["path"]
        name = item["name"]

        row_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        row_frame.grid(row=row_idx, column=0, sticky="ew", pady=2)
        row_frame.columnconfigure(0, weight=1)

        btn = ctk.CTkButton(
            row_frame,
            text=f"📂  {name}",
            anchor="w",
            fg_color="transparent",
            hover_color=("#d4edda", "#1e4d35"),
            text_color=("gray10", "gray90"),
            font=ctk.CTkFont(family="맑은 고딕", size=15, weight="bold"),
            command=lambda p=path: self._select_folder(p),
        )
        btn.grid(row=0, column=0, sticky="ew")
        self._buttons.append(btn)

        # 우클릭 컨텍스트 메뉴
        btn.bind("<Button-3>", lambda e, p=path: self._show_context_menu(e, p))

    def _select_folder(self, path: str):
        if not os.path.isdir(path):
            messagebox.showwarning("경고", f"폴더를 찾을 수 없습니다:\n{path}")
            self._load()
            return
        self._selected_path = path
        self._on_folder_selected(path)

    def _add_folder(self):
        path = filedialog.askdirectory(title="즐겨찾기에 추가할 폴더를 선택하세요")
        if not path:
            return
        favorites_store.add_favorite(path)
        self._load()

    def _show_context_menu(self, event, path: str):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="이름 변경", command=lambda: self._rename(path))
        menu.add_separator()
        menu.add_command(label="목록에서 제거", command=lambda: self._remove(path))
        menu.tk_popup(event.x_root, event.y_root)

    def _rename(self, path: str):
        current_name = os.path.basename(path)
        new_name = simpledialog.askstring(
            "이름 변경",
            f"새 표시 이름을 입력하세요:",
            initialvalue=current_name,
            parent=self,
        )
        if new_name and new_name.strip():
            favorites_store.rename_favorite(path, new_name.strip())
            self._load()

    def _remove(self, path: str):
        if messagebox.askyesno("확인", "즐겨찾기 목록에서 제거하시겠습니까?\n(실제 폴더는 삭제되지 않습니다)"):
            favorites_store.remove_favorite(path)
            self._load()

    # ── 저장 / 불러오기 ──────────────────────────────────────────────────
    def _save_to_file(self):
        """현재 즐겨찾기를 사용자가 선택한 경로에 JSON으로 내보냕니다."""
        path = filedialog.asksaveasfilename(
            title="즐겨찾기 설정 저장",
            defaultextension=".json",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
            initialfile="favorites_backup.json",
        )
        if not path:
            return
        try:
            export_favorites(path)
            messagebox.showinfo("저장 완료", f"즐겨찾기 설정이 저장되었습니다:\n{path}")
        except OSError as e:
            messagebox.showerror("저장 실패", str(e))

    def _load_from_file(self):
        """외부 JSON에서 즐겨찾기를 불러와 병합합니다."""
        path = filedialog.askopenfilename(
            title="즐겨찾기 설정 불러오기",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
        )
        if not path:
            return
        try:
            import_favorites(path)
            self._load()
            messagebox.showinfo("불러오기 완료", "자젠찾기 설정을 불러왔습니다.")
        except (OSError, ValueError) as e:
            messagebox.showerror("불러오기 실패", str(e))
