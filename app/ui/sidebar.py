"""
즐겨찾기 사이드바 패널.
- 주간/월간/미분류 그룹 트리 표시
- 그룹 헤더에 일괄 생성 버튼
- 그룹 내 드래그로 순서 변경 (고스트 창이 커서를 따라다님)
- 우클릭으로 그룹 변경/이름변경/삭제
"""

import os
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from typing import Callable, Dict, List, Optional, Tuple

import customtkinter as ctk

from app.storage import favorites_store
from app.storage.favorites_store import export_favorites, import_favorites

_DRAG_THRESHOLD = 5

_GROUPS = [
    {
        "key": "weekly",
        "label": "🗓  주간",
        "header_color": ("#dbeafe", "#1e3a5f"),
        "text_color": ("#1d6aab", "#60a5fa"),
        "btn_fg": ("#1d6aab", "#1a5a99"),
        "btn_hover": ("#155588", "#124a7d"),
    },
    {
        "key": "monthly",
        "label": "📅  월간",
        "header_color": ("#ede9fe", "#2d1b4e"),
        "text_color": ("#7b2d8b", "#c084fc"),
        "btn_fg": ("#7b2d8b", "#5e1f6e"),
        "btn_hover": ("#5e1f6e", "#4a1a5a"),
    },
    {
        "key": "unknown",
        "label": "❓  미분류",
        "header_color": ("gray88", "#333333"),
        "text_color": ("gray40", "gray60"),
        "btn_fg": None,
        "btn_hover": None,
    },
]

_GROUP_MAP: Dict[str, Dict] = {g["key"]: g for g in _GROUPS}


class SidebarFrame(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_folder_selected: Callable[[str], None],
        on_batch_generate: Optional[Callable[[str, List[str]], None]] = None,
        **kwargs,
    ):
        kwargs.setdefault("fg_color", ("white", "#2b2b2b"))
        super().__init__(master, **kwargs)
        self._on_folder_selected = on_folder_selected
        self._on_batch_generate = on_batch_generate

        # 드래그 상태
        self._drag_group: Optional[str] = None
        self._drag_idx: Optional[int] = None
        self._drag_start_y: int = 0
        self._is_dragging: bool = False
        self._drop_idx: Optional[int] = None
        self._drag_name: str = ""
        self._ghost: Optional[tk.Toplevel] = None

        # 그룹별 행 데이터 {group_key: [(row_frame, path), ...]}
        self._group_rows: Dict[str, List[Tuple[ctk.CTkFrame, str]]] = {
            g["key"]: [] for g in _GROUPS
        }

        self._build_ui()
        self._load()

    # ── UI 구성 ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="📁  즐겨찾기 폴더",
            font=ctk.CTkFont(family="맑은 고딕", size=13, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        self._scroll = ctk.CTkScrollableFrame(
            self, label_text="", fg_color=("white", "#2b2b2b")
        )
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)
        self._scroll.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ctk.CTkButton(
            self,
            text="＋  폴더 추가",
            command=self._add_folder,
            height=34,
            font=ctk.CTkFont(family="맑은 고딕", size=12),
            fg_color="#2d6a4f",
            hover_color="#1b4332",
        ).grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 2))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 10))
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_row,
            text="파일로 저장",
            command=self._save_to_file,
            height=30,
            font=ctk.CTkFont(family="맑은 고딕", size=11),
            fg_color=("#1d6aab", "#1a5a99"),
            hover_color=("#155588", "#124a7d"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 2))

        ctk.CTkButton(
            btn_row,
            text="불러오기",
            command=self._load_from_file,
            height=30,
            font=ctk.CTkFont(family="맑은 고딕", size=11),
            fg_color=("gray60", "gray40"),
            hover_color=("gray50", "gray30"),
        ).grid(row=0, column=1, sticky="ew", padx=(2, 0))

    # ── 목록 로드 ─────────────────────────────────────────────────────────────
    def _load(self):
        for widget in self._scroll.winfo_children():
            widget.destroy()
        for key in self._group_rows:
            self._group_rows[key].clear()

        favorites = favorites_store.load_favorites()

        grouped: Dict[str, List[Dict]] = {g["key"]: [] for g in _GROUPS}
        for item in favorites:
            gk = item.get("group", "unknown")
            if gk not in grouped:
                gk = "unknown"
            grouped[gk].append(item)

        scroll_row = 0
        for g_info in _GROUPS:
            gk = g_info["key"]
            items = grouped[gk]
            scroll_row = self._add_group_header(scroll_row, g_info, items)
            for item in items:
                self._add_item_row(scroll_row, gk, len(self._group_rows[gk]), item)
                scroll_row += 1

    def _add_group_header(self, scroll_row: int, g_info: Dict, items: List[Dict]) -> int:
        hdr = ctk.CTkFrame(
            self._scroll, fg_color=g_info["header_color"], corner_radius=6
        )
        hdr.grid(row=scroll_row, column=0, sticky="ew", pady=(6, 1), padx=2)
        hdr.columnconfigure(0, weight=1)

        count_text = f" ({len(items)})" if items else " (0)"
        ctk.CTkLabel(
            hdr,
            text=g_info["label"] + count_text,
            font=ctk.CTkFont(family="맑은 고딕", size=11, weight="bold"),
            text_color=g_info["text_color"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=8, pady=4)

        # 주간/월간만 일괄 생성 버튼 표시 (항목 있을 때만)
        if g_info["btn_fg"] is not None and items:
            gk = g_info["key"]
            ctk.CTkButton(
                hdr,
                text="일괄 생성 ▶",
                width=82,
                height=22,
                font=ctk.CTkFont(family="맑은 고딕", size=10, weight="bold"),
                fg_color=g_info["btn_fg"],
                hover_color=g_info["btn_hover"],
                command=lambda k=gk: self._batch_generate(k),
            ).grid(row=0, column=1, padx=(0, 6), pady=4)

        return scroll_row + 1

    def _add_item_row(self, scroll_row: int, group_key: str, group_idx: int, item: Dict):
        path = item["path"]
        name = item["name"]

        row_frame = ctk.CTkFrame(self._scroll, fg_color="transparent", cursor="hand2")
        row_frame.grid(row=scroll_row, column=0, sticky="ew", pady=1, padx=4)
        row_frame.columnconfigure(1, weight=1)

        # 드래그 핸들 (≡)
        handle = ctk.CTkLabel(
            row_frame,
            text="≡",
            width=18,
            text_color=("gray65", "gray50"),
            font=ctk.CTkFont(size=14),
            cursor="fleur",
        )
        handle.grid(row=0, column=0, padx=(2, 0))

        btn = ctk.CTkButton(
            row_frame,
            text=f"📂  {name}",
            anchor="w",
            fg_color="transparent",
            hover_color=("#d4edda", "#1e4d35"),
            text_color=("gray10", "gray90"),
            font=ctk.CTkFont(family="맑은 고딕", size=14, weight="bold"),
            command=None,
        )
        btn.grid(row=0, column=1, sticky="ew")

        for w in (row_frame, handle, btn):
            w.bind("<Button-1>",        lambda e, gk=group_key, gi=group_idx, n=name: self._drag_start(e, gk, gi, n))
            w.bind("<B1-Motion>",       self._drag_motion)
            w.bind("<ButtonRelease-1>", lambda e, gk=group_key, p=path: self._drag_end(e, gk, p))

        for w in (row_frame, btn):
            w.bind("<Button-3>", lambda e, gk=group_key, p=path: self._show_context_menu(e, gk, p))

        self._group_rows[group_key].append((row_frame, path))

    # ── 드래그 앤 드롭 ───────────────────────────────────────────────────────
    def _drag_start(self, event, group_key: str, group_idx: int, name: str):
        self._drag_group = group_key
        self._drag_idx = group_idx
        self._drag_start_y = event.y_root
        self._is_dragging = False
        self._drop_idx = group_idx
        self._drag_name = name

    def _drag_motion(self, event):
        if self._drag_idx is None:
            return
        if abs(event.y_root - self._drag_start_y) < _DRAG_THRESHOLD:
            return
        self._is_dragging = True
        self._move_ghost(event)

        rows = self._group_rows.get(self._drag_group, [])
        new_tgt = len(rows)
        for i, (rf, _) in enumerate(rows):
            try:
                ry = rf.winfo_rooty()
                rh = rf.winfo_height()
                if event.y_root < ry + rh // 2:
                    new_tgt = i
                    break
            except tk.TclError:
                pass
        if new_tgt != self._drop_idx:
            self._drop_idx = new_tgt
            self._update_drag_visual()

    def _create_ghost(self, name: str, x: int, y: int) -> tk.Toplevel:
        ghost = tk.Toplevel(self)
        ghost.overrideredirect(True)
        ghost.attributes("-topmost", True)
        ghost.attributes("-alpha", 0.80)
        ghost.configure(bg="#2d6a4f")
        tk.Label(
            ghost,
            text=f"  📂  {name}  ",
            bg="#2d6a4f",
            fg="white",
            font=("맑은 고딕", 12, "bold"),
            padx=6,
            pady=3,
        ).pack()
        ghost.geometry(f"+{x + 14}+{y - 16}")
        return ghost

    def _move_ghost(self, event):
        if self._ghost is None:
            self._ghost = self._create_ghost(self._drag_name, event.x_root, event.y_root)
        else:
            try:
                self._ghost.geometry(f"+{event.x_root + 14}+{event.y_root - 16}")
            except tk.TclError:
                self._ghost = None

    def _destroy_ghost(self):
        if self._ghost is not None:
            try:
                self._ghost.destroy()
            except tk.TclError:
                pass
            self._ghost = None

    def _update_drag_visual(self):
        src = self._drag_idx
        tgt = self._drop_idx
        rows = self._group_rows.get(self._drag_group, [])
        for i, (rf, _) in enumerate(rows):
            try:
                if i == src:
                    rf.configure(fg_color=("#b7e4c7", "#1e4d35"))
                elif i == tgt and i != src:
                    rf.configure(fg_color=("#d4edda", "#2a6040"))
                else:
                    rf.configure(fg_color="transparent")
            except tk.TclError:
                pass

    def _drag_end(self, event, group_key: str, path: str):
        self._destroy_ghost()

        if not self._is_dragging:
            self._clear_drag_visual()
            self._drag_group = None
            self._drag_idx = None
            self._is_dragging = False
            self._drop_idx = None
            self._select_folder(path)
            return

        src = self._drag_idx
        dst = self._drop_idx
        gk = self._drag_group

        self._drag_group = None
        self._drag_idx = None
        self._is_dragging = False
        self._drop_idx = None

        if src is None or dst is None or src == dst:
            self._clear_drag_visual()
            return

        rows = self._group_rows.get(gk, [])
        group_paths = [p for _, p in rows]
        moved = group_paths.pop(src)
        adj = dst - 1 if dst > src else dst
        group_paths.insert(adj, moved)

        # 전체 favorites를 그룹 순서 유지하며 재저장
        all_favs = favorites_store.load_favorites()
        fav_map: Dict[str, Dict] = {os.path.normpath(f["path"]): f for f in all_favs}

        all_groups: Dict[str, List] = {g["key"]: [] for g in _GROUPS}
        for f in all_favs:
            fgk = f.get("group", "unknown")
            if fgk not in all_groups:
                fgk = "unknown"
            if fgk != gk:
                all_groups[fgk].append(f)
        all_groups[gk] = [
            fav_map[os.path.normpath(p)]
            for p in group_paths
            if os.path.normpath(p) in fav_map
        ]

        final: List[Dict] = []
        for g_info in _GROUPS:
            final.extend(all_groups[g_info["key"]])
        favorites_store.save_favorites(final)
        self._load()

    def _clear_drag_visual(self):
        for gk in self._group_rows:
            for rf, _ in self._group_rows[gk]:
                try:
                    rf.configure(fg_color="transparent")
                except tk.TclError:
                    pass

    # ── 일괄 생성 ────────────────────────────────────────────────────────────
    def _batch_generate(self, group_key: str):
        if self._on_batch_generate is None:
            messagebox.showinfo("일괄 생성", "일괄 생성 기능이 연결되지 않았습니다.")
            return
        rows = self._group_rows.get(group_key, [])
        paths = [p for _, p in rows]
        if not paths:
            messagebox.showinfo("일괄 생성", "해당 그룹에 폴더가 없습니다.")
            return
        self._on_batch_generate(group_key, paths)

    # ── 폴더 선택 / 추가 / 우클릭 ───────────────────────────────────────────
    def _select_folder(self, path: str):
        if not os.path.isdir(path):
            messagebox.showwarning("경고", f"폴더를 찾을 수 없습니다:\n{path}")
            self._load()
            return
        self._on_folder_selected(path)

    def _add_folder(self):
        path = filedialog.askdirectory(title="즐겨찾기에 추가할 폴더를 선택하세요")
        if not path:
            return
        favorites_store.add_favorite(path)
        self._load()

    def _show_context_menu(self, event, group_key: str, path: str):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="이름 변경", command=lambda: self._rename(path))
        menu.add_separator()
        sub = tk.Menu(menu, tearoff=0)
        for g_info in _GROUPS:
            if g_info["key"] != group_key:
                sub.add_command(
                    label=g_info["label"],
                    command=lambda gk=g_info["key"], p=path: self._change_group(p, gk),
                )
        menu.add_cascade(label="그룹 변경", menu=sub)
        menu.add_separator()
        menu.add_command(label="목록에서 제거", command=lambda: self._remove(path))
        menu.tk_popup(event.x_root, event.y_root)

    def _change_group(self, path: str, new_group: str):
        favs = favorites_store.load_favorites()
        normalized = os.path.normpath(path)
        for item in favs:
            if os.path.normpath(item["path"]) == normalized:
                item["group"] = new_group
                break
        favorites_store.save_favorites(favs)
        self._load()

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
        if messagebox.askyesno(
            "확인", "즐겨찾기 목록에서 제거하시겠습니까?\n(실제 폴더는 삭제되지 않습니다)"
        ):
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