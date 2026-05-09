"""
즐겨찾기 사이드바 패널.
폴더 목록 표시, 추가/삭제/이름변경/드래그 순서 변경, 주간·월간 그룹 배지 기능 제공.
"""

import os
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from typing import Callable, List, Dict, Optional

import customtkinter as ctk

from app.storage import favorites_store
from app.storage.favorites_store import export_favorites, import_favorites

# 드래그로 인식하는 최소 이동 픽셀 (클릭과 구분)
_DRAG_THRESHOLD = 5

# 그룹 배지 스타일 (light/dark 각각)
_BADGE_STYLES: Dict[str, Dict] = {
    "weekly":  {"color": ("#1d6aab", "#1a5a99"), "text": "주간"},
    "monthly": {"color": ("#7b2d8b", "#5e1f6e"), "text": "월간"},
    "unknown": {"color": ("gray55", "gray42"),   "text": "?"},
}


class SidebarFrame(ctk.CTkFrame):
    def __init__(self, master, on_folder_selected: Callable[[str], None], **kwargs):
        kwargs.setdefault("fg_color", ("white", "#2b2b2b"))
        super().__init__(master, **kwargs)
        self._on_folder_selected = on_folder_selected
        self._selected_path: str = ""

        # 드래그 상태 변수
        self._drag_source_idx: Optional[int] = None
        self._drag_start_y: int = 0
        self._is_dragging: bool = False
        self._drop_target_idx: Optional[int] = None

        # 행 순서 관리
        self._row_frames: List[ctk.CTkFrame] = []
        self._row_paths: List[str] = []

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

        # 하단 버튼 행 (저장 / 불러오기)
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

    # ── 목록 로드 ─────────────────────────────────────────────────────────────
    def _load(self):
        """즐겨찾기 목록을 다시 로드하여 UI를 갱신합니다."""
        for widget in self._scroll.winfo_children():
            widget.destroy()
        self._row_frames.clear()
        self._row_paths.clear()

        favorites = favorites_store.load_favorites()
        for i, item in enumerate(favorites):
            self._add_row(i, item)

    def _add_row(self, row_idx: int, item: Dict):
        path = item["path"]
        name = item["name"]
        group = item.get("group", "unknown")

        row_frame = ctk.CTkFrame(self._scroll, fg_color="transparent", cursor="hand2")
        row_frame.grid(row=row_idx, column=0, sticky="ew", pady=2)
        row_frame.columnconfigure(0, weight=1)

        # 폴더 버튼 (command=None -> ButtonRelease에서 클릭/드래그 구분 처리)
        btn = ctk.CTkButton(
            row_frame,
            text=f"📂  {name}",
            anchor="w",
            fg_color="transparent",
            hover_color=("#d4edda", "#1e4d35"),
            text_color=("gray10", "gray90"),
            font=ctk.CTkFont(family="맑은 고딕", size=15, weight="bold"),
            command=None,
        )
        btn.grid(row=0, column=0, sticky="ew")

        # 그룹 배지
        style = _BADGE_STYLES.get(group, _BADGE_STYLES["unknown"])
        badge = ctk.CTkLabel(
            row_frame,
            text=style["text"],
            font=ctk.CTkFont(family="맑은 고딕", size=10, weight="bold"),
            fg_color=style["color"],
            text_color="white",
            corner_radius=4,
            width=34,
            height=18,
        )
        badge.grid(row=0, column=1, padx=(0, 6), pady=4)

        # 드래그·클릭 이벤트 바인딩 (row_frame, btn, badge 모두)
        for widget in (row_frame, btn, badge):
            widget.bind("<Button-1>",        lambda e, i=row_idx: self._drag_start(e, i))
            widget.bind("<B1-Motion>",       self._drag_motion)
            widget.bind("<ButtonRelease-1>", lambda e, p=path: self._drag_end(e, p))

        # 우클릭 컨텍스트 메뉴
        for widget in (row_frame, btn):
            widget.bind("<Button-3>", lambda e, p=path: self._show_context_menu(e, p))

        self._row_frames.append(row_frame)
        self._row_paths.append(path)

    # ── 드래그 앤 드롭 ───────────────────────────────────────────────────────
    def _drag_start(self, event, idx: int):
        self._drag_source_idx = idx
        self._drag_start_y = event.y_root
        self._is_dragging = False
        self._drop_target_idx = idx

    def _drag_motion(self, event):
        if self._drag_source_idx is None:
            return
        if abs(event.y_root - self._drag_start_y) < _DRAG_THRESHOLD:
            return

        self._is_dragging = True
        target = self._calc_drop_idx(event.y_root)
        if target != self._drop_target_idx:
            self._drop_target_idx = target
            self._update_drag_visual()

    def _calc_drop_idx(self, y_root: int) -> int:
        """마우스 절대 Y 좌표를 기준으로 삽입될 인덱스를 계산합니다."""
        count = len(self._row_frames)
        if count == 0:
            return 0
        for i, rf in enumerate(self._row_frames):
            try:
                ry = rf.winfo_rooty()
                rh = rf.winfo_height()
                if y_root < ry + rh // 2:
                    return i
            except tk.TclError:
                pass
        return count

    def _update_drag_visual(self):
        """드래그 중 시각적 피드백을 업데이트합니다."""
        src = self._drag_source_idx
        tgt = self._drop_target_idx
        for i, rf in enumerate(self._row_frames):
            try:
                if i == src:
                    rf.configure(fg_color=("#b7e4c7", "#1e4d35"))
                elif i == tgt and i != src:
                    rf.configure(fg_color=("#d4edda", "#2a6040"))
                else:
                    rf.configure(fg_color="transparent")
            except tk.TclError:
                pass

    def _drag_end(self, event, path: str):
        if not self._is_dragging:
            # 임계값 미만이면 클릭으로 처리
            self._clear_drag_visual()
            self._drag_source_idx = None
            self._is_dragging = False
            self._drop_target_idx = None
            self._select_folder(path)
            return

        src = self._drag_source_idx
        dst = self._drop_target_idx

        self._drag_source_idx = None
        self._is_dragging = False
        self._drop_target_idx = None

        if src is None or dst is None or src == dst:
            self._clear_drag_visual()
            return

        # pop(src) 후 insert(dst) — dst > src이면 인덱스 1 감소
        new_paths = list(self._row_paths)
        item_path = new_paths.pop(src)
        adjusted_dst = dst - 1 if dst > src else dst
        new_paths.insert(adjusted_dst, item_path)

        favorites_store.reorder_favorites(new_paths)
        self._load()

    def _clear_drag_visual(self):
        for rf in self._row_frames:
            try:
                rf.configure(fg_color="transparent")
            except tk.TclError:
                pass

    # ── 폴더 선택 / 추가 / 우클릭 ───────────────────────────────────────────
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
            "새 표시 이름을 입력하세요:",
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

    # ── 저장 / 불러오기 ──────────────────────────────────────────────────────
    def _save_to_file(self):
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
        path = filedialog.askopenfilename(
            title="즐겨찾기 설정 불러오기",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
        )
        if not path:
            return
        try:
            import_favorites(path)
            self._load()
            messagebox.showinfo("불러오기 완료", "즐겨찾기 설정을 불러왔습니다.")
        except (OSError, ValueError) as e:
            messagebox.showerror("불러오기 실패", str(e))